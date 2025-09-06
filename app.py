import eventlet
eventlet.monkey_patch()

import random
from collections import Counter
import functools
import time
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from game_logic import Tile, get_combination_info, is_stronger_combination

# ===================================================================
# 2. Flask 및 SocketIO 설정
# ===================================================================
app = Flask(__name__)
app.config['SECRET_KEY'] = 'a_very_secret_key'
socketio = SocketIO(app)

# ===================================================================
# 3. 서버 측 게임 상태 관리
# ===================================================================
players = {} 
game_state = {}
player_money = []
round_number = 1
num_players = 0
tiles_per_player = 0

def start_new_game(is_first_game=True):
    global game_state, round_number, player_money
    if is_first_game:
        player_money = [27] * num_players
        round_number = 1
    else:
        round_number += 1
    
    suits, ranks = ["cloud", "star", "moon", "sun"], list(range(1, 16))
    deck = [Tile(suit, rank) for suit in suits for rank in ranks]
    random.shuffle(deck)
    player_hands = [[] for _ in range(num_players)]
    for _ in range(tiles_per_player):
        for i in range(num_players):
            player_hands[i].append(deck.pop())
    for hand in player_hands: hand.sort()
    
    # ✨ 수정된 부분: 시작 플레이어 결정 방식 변경
    # 1. 먼저 랜덤하게 선을 정합니다.
    start_player_index = random.randint(0, num_players - 1)
    
    # 2. '구름 3'을 가진 사람이 있는지 확인하고, 있다면 그 사람으로 선을 변경합니다.
    starting_tile = Tile("cloud", 3)
    for i, hand in enumerate(player_hands):
        if starting_tile in hand:
            start_player_index = i
            break
    
    game_state = {
        "player_hands": player_hands,
        "current_player_index": start_player_index,
        "last_played_hand_info": (None, None),
        "last_played_tiles": [],
        "players_who_passed_this_round": [],
        "last_player_to_act_index": start_player_index,
        "game_log": [f"라운드 {round_number} 시작!"]
    }
    print(f"✨ Round {round_number} started! Starting player is {start_player_index + 1}")

def handle_end_of_round(winner_index):
    """ ✨ 수정: '2' 카드 2배 지불 규칙이 적용된 라운드 종료 함수 """
    global player_money
    print(f"--- Round {round_number} End ---")
    final_card_counts = [len(hand) for hand in game_state['player_hands']]
    payments = []
    
    for i in range(num_players):
        for j in range(num_players):
            if i == j: continue

            if final_card_counts[j] > final_card_counts[i]:
                # 기본 지불 금액은 카드 수 차이
                payment_amount = final_card_counts[j] - final_card_counts[i]
                
                # 받는 사람(i)이 이번 라운드 승자인지 확인
                if i == winner_index:
                    paying_hand = game_state['player_hands'][j]
                    # 내는 사람(j)의 패에 '2'가 있는지 확인
                    has_two = any(tile.rank == 2 for tile in paying_hand)
                    if has_two:
                        payment_amount *= 2 # 2배로!
                
                player_money[i] += payment_amount
                player_money[j] -= payment_amount
                payments.append(f"플레이어 {j + 1} → 플레이어 {i + 1}에게 {payment_amount}원 지불")
    
    socketio.emit('round_result', {
        'winner': winner_index + 1, 'payments': payments, 'money_status': player_money
    })
    
    return any(money <= 0 for money in player_money)

def get_final_rankings():
    survivors, bankrupt_players = [], []
    for i, money in enumerate(player_money):
        if money > 0: survivors.append((money, i + 1))
        else: bankrupt_players.append(i + 1)
    survivors.sort(reverse=True)
    ranking_text = [f"{rank + 1}등: 플레이어 {p_num} ({money}원)" for rank, (money, p_num) in enumerate(survivors)]
    bankrupt_text = [str(p_num) for p_num in bankrupt_players]
    return {'rankings': ranking_text, 'bankrupt': bankrupt_text}

def broadcast_game_state():
    game_state_for_client = game_state.copy()
    game_state_for_client['player_hands'] = [[tile.to_dict() for tile in hand] for hand in game_state['player_hands']]
    game_state_for_client['last_played_tiles'] = [tile.to_dict() for tile in game_state['last_played_tiles']]
    game_state_for_client['player_money'] = player_money
    combo_name, rep_info = game_state['last_played_hand_info']
    if isinstance(rep_info, tuple): rep_info_dict = [tile.to_dict() for tile in rep_info]
    elif isinstance(rep_info, Tile): rep_info_dict = rep_info.to_dict()
    else: rep_info_dict = None
    game_state_for_client['last_played_hand_info'] = (combo_name, rep_info_dict)
    socketio.emit('game_update', game_state_for_client)

def reset_game():
    global players, game_state, player_money, round_number, num_players, tiles_per_player
    players.clear()
    game_state.clear()
    player_money.clear()
    round_number = 1
    num_players = 0
    tiles_per_player = 0
    print("🔄 Game has been reset.")
    socketio.emit('show_lobby')

# ===================================================================
# 4. 라우트 및 이벤트 핸들러
# ===================================================================
@app.route('/')
def home():
    return render_template('index.html')

@socketio.on('request_start_game')
def on_request_start_game(data):
    global num_players, tiles_per_player
    if num_players != 0: return
    num_players = int(data.get('num_players', 3))
    if num_players == 3: tiles_per_player = 15
    elif num_players == 4: tiles_per_player = 13
    elif num_players == 5: tiles_per_player = 12
    
    sid = request.sid
    if sid not in players:
        players[sid] = 0
        print(f"✅ Player 1 (SID: {sid}) created a {num_players}-player game.")
        emit('player_assigned', {'player_num': 0}, room=sid)
    socketio.emit('waiting_for_players', {'current': len(players), 'needed': num_players})

@socketio.on('connect')
def handle_connect():
    sid = request.sid
    if num_players == 0 or len(players) >= num_players or sid in players: return
    player_num = len(players)
    players[sid] = player_num
    print(f"✅ Player {player_num + 1} (SID: {sid}) connected.")
    emit('player_assigned', {'player_num': player_num}, room=sid)
    socketio.emit('waiting_for_players', {'current': len(players), 'needed': num_players})
    if len(players) == num_players:
        start_new_game(is_first_game=True)
        game_state_for_client = game_state.copy()
        game_state_for_client['player_hands'] = [[tile.to_dict() for tile in hand] for hand in game_state['player_hands']]
        game_state_for_client['last_played_tiles'] = [tile.to_dict() for tile in game_state['last_played_tiles']]
        game_state_for_client['player_money'] = player_money
        combo_name, rep_info = game_state['last_played_hand_info']
        if isinstance(rep_info, tuple): rep_info_dict = [tile.to_dict() for tile in rep_info]
        elif isinstance(rep_info, Tile): rep_info_dict = rep_info.to_dict()
        else: rep_info_dict = None
        game_state_for_client['last_played_hand_info'] = (combo_name, rep_info_dict)
        socketio.emit('game_started', game_state_for_client)

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    if sid in players:
        player_num = players[sid]
        print(f"❌ Player {player_num + 1} (SID: {sid}) disconnected.")
        socketio.emit('player_left', {'player_num': player_num + 1})
        reset_game()

@socketio.on('play_hand')
def handle_play_hand(hand_data):
    sid, player_num = request.sid, players.get(request.sid)
    if player_num is None or not game_state: return
    if player_num != game_state.get('current_player_index'):
        return emit('error_message', {'message': '당신의 턴이 아닙니다.'})
    
    # ✨ 추가: 이미 패스한 플레이어는 패를 낼 수 없음
    if player_num in game_state.get('players_who_passed_this_round', []):
        return emit('error_message', {'message': '이미 패스했으므로 이번 라운드에 참여할 수 없습니다.'})

    submitted_tiles = [Tile(t['suit'], t['rank']) for t in hand_data]
    combo_info = get_combination_info(submitted_tiles)
    if not combo_info[0]: return emit('error_message', {'message': '유효한 조합이 아닙니다.'})
    if not is_stronger_combination(combo_info, game_state['last_played_hand_info']):
        return emit('error_message', {'message': '더 약한 패는 낼 수 없습니다.'})
    
    combo_name, rep_info = combo_info
    rep_rank = rep_info[0].rank if isinstance(rep_info, tuple) else rep_info.rank
    log_message = f"P{player_num + 1}: {rep_rank} {combo_name}을(를) 냈습니다."
    game_state['game_log'].append(log_message)
    if len(game_state['game_log']) > 15: game_state['game_log'].pop(0)

    # ✨ 수정: 여기서 패스 기록을 초기화하는 코드를 완전히 삭제했습니다.
    game_state.update({
        'last_played_hand_info': combo_info,
        'last_played_tiles': submitted_tiles,
        'last_player_to_act_index': player_num
    })
    
    current_hand = game_state['player_hands'][player_num]
    for tile in submitted_tiles:
        if tile in current_hand: current_hand.remove(tile)
    
    if not current_hand:
        is_game_over = handle_end_of_round(winner_index=player_num)
        if is_game_over:
            final_ranks = get_final_rankings()
            socketio.emit('game_over', final_ranks)
        else:
            start_new_game(is_first_game=False)
            broadcast_game_state()
    else:
        game_state['current_player_index'] = (player_num + 1) % num_players
        broadcast_game_state()

@socketio.on('pass_turn')
def handle_pass_turn():
    sid, player_num = request.sid, players.get(request.sid)
    if player_num is None or not game_state: return
    if player_num != game_state.get('current_player_index'):
        return emit('error_message', {'message': '당신의 턴이 아닙니다.'})
    if game_state['last_played_hand_info'][0] is None:
        return emit('error_message', {'message': '라운드의 선두는 패스할 수 없습니다.'})
    
    # ✨ 추가: 이미 패스한 플레이어는 다시 패스할 수 없음
    if player_num in game_state.get('players_who_passed_this_round', []):
        return # 조용히 무시

    game_state['players_who_passed_this_round'].append(player_num)
    
    log_message = f"P{player_num + 1}: 패스했습니다."
    game_state['game_log'].append(log_message)
    if len(game_state['game_log']) > 15: game_state['game_log'].pop(0)
    
    active_players_count = num_players - len(game_state['players_who_passed_this_round'])
    if active_players_count <= 1:
        game_state.update({
            'last_played_hand_info': (None, None),
            'last_played_tiles': [],
            'players_who_passed_this_round': [],
            'current_player_index': game_state['last_player_to_act_index']
        })
    else:
        game_state['current_player_index'] = (player_num + 1) % num_players
    
    broadcast_game_state()

@socketio.on('request_new_game')
def on_request_new_game():
    if len(players) > 0:
        reset_game()

# ===================================================================
# 5. 서버 실행
# ===================================================================
if __name__ == '__main__':
    socketio.run(app, debug=True)