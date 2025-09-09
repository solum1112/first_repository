import eventlet
eventlet.monkey_patch()
import random
from collections import Counter
import functools
import time
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit



from game_logic import Tile, get_combination_info, is_stronger_combination

app = Flask(__name__)
app.config['SECRET_KEY'] = 'a_very_secret_key'
socketio = SocketIO(app)

players = {} 
game_state = {}
player_money = []
round_number = 1
num_players = 0
tiles_per_player = 0

def start_new_game(is_first_game=True):
    global game_state, round_number, player_money
    if is_first_game:
        player_money = [48] * num_players
        round_number = 1
    else:
        round_number += 1
    
    suits, ranks = ["cloud", "star", "moon", "sun"], list(range(1, 16))
    deck = [Tile(suit, rank) for suit in suits for rank in ranks]
    random.shuffle(deck)
    player_hands = [[] for _ in range(num_players)]
    for _ in range(tiles_per_player):
        for i in range(num_players): player_hands[i].append(deck.pop())
    for hand in player_hands: hand.sort()
    
    start_player_index = random.randint(0, num_players - 1)
    starting_tile = Tile("cloud", 3)
    for i, hand in enumerate(player_hands):
        if starting_tile in hand:
            start_player_index = i
            break
    
    game_state = {
        "player_hands": player_hands, "current_player_index": start_player_index,
        "last_played_hand_info": (None, None), "last_played_tiles": [],
        "players_who_passed_this_round": [], "last_player_to_act_index": start_player_index,
        "game_log": [f"라운드 {round_number} 시작!"]
    }
    print(f"✨ Round {round_number} started! Starting player is {start_player_index + 1}")

def handle_end_of_round(winner_index):
    global player_money
    final_card_counts = [len(hand) for hand in game_state['player_hands']]
    payments = []
    for i in range(num_players):
        for j in range(num_players):
            if i == j: continue
            if final_card_counts[j] > final_card_counts[i]:
                payment_amount = final_card_counts[j] - final_card_counts[i]
                if i == winner_index and any(tile.rank == 2 for tile in game_state['player_hands'][j]):
                    payment_amount *= 2
                player_money[i] += payment_amount
                player_money[j] -= payment_amount
                payments.append(f"P{j + 1} → P{i + 1}에게 {payment_amount}원 지불")
    
    socketio.emit('round_result', {'winner': winner_index + 1, 'payments': payments, 'money_status': player_money})
    return any(money <= 0 for money in player_money)

def get_final_rankings():
    survivors = sorted([(money, i + 1) for i, money in enumerate(player_money) if money > 0], reverse=True)
    bankrupt_players = [i + 1 for i, money in enumerate(player_money) if money <= 0]
    ranking_text = [f"{rank + 1}등: P{p_num} ({money}원)" for rank, (money, p_num) in enumerate(survivors)]
    return {'rankings': ranking_text, 'bankrupt': [str(p) for p in bankrupt_players]}

def broadcast_game_state(is_start=False):
    game_state_for_client = game_state.copy()
    game_state_for_client['player_hands'] = [[tile.to_dict() for tile in hand] for hand in game_state['player_hands']]
    game_state_for_client['last_played_tiles'] = [tile.to_dict() for tile in game_state['last_played_tiles']]
    game_state_for_client['player_money'] = player_money
    combo_name, rep_info = game_state['last_played_hand_info']
    if isinstance(rep_info, tuple): rep_info_dict = [tile.to_dict() for tile in rep_info]
    elif isinstance(rep_info, Tile): rep_info_dict = rep_info.to_dict()
    else: rep_info_dict = None
    game_state_for_client['last_played_hand_info'] = (combo_name, rep_info_dict)
    event_name = 'game_started' if is_start else 'game_update'
    socketio.emit(event_name, game_state_for_client)

def reset_game():
    global players, game_state, num_players
    players.clear(); game_state.clear(); num_players = 0
    print("🔄 Game has been reset.")
    socketio.emit('show_lobby')

def advance_turn():
    if not game_state: return
    print(f"--- ADVANCE TURN ---") # 디버깅 메시지
    print(f"Before advancing, current player is {game_state['current_player_index'] + 1}") # 디버깅 메시지
    print(f"Pass list is: {game_state['players_who_passed_this_round']}") # 디버깅 메시지
    
    current_player = game_state['current_player_index']
    next_player = (current_player + 1) % num_players
    for _ in range(num_players):
        if next_player not in game_state['players_who_passed_this_round']:
            game_state['current_player_index'] = next_player
            print(f"Next active player found: {next_player + 1}") # 디버깅 메시지
            return
        print(f"Player {next_player + 1} has passed, skipping.") # 디버깅 메시지
        next_player = (next_player + 1) % num_players

@app.route('/')
def home(): return render_template('index.html')

@socketio.on('request_start_game')
def on_request_start_game(data):
    global num_players, tiles_per_player
    if num_players != 0: return
    num_players = int(data.get('num_players', 3))
    if num_players == 3: tiles_per_player = 12
    elif num_players == 4: tiles_per_player = 13
    else: tiles_per_player = 12
    sid = request.sid
    if sid not in players:
        players[sid] = 0
        emit('player_assigned', {'player_num': 0}, room=sid)
    socketio.emit('waiting_for_players', {'current': len(players), 'needed': num_players})

@socketio.on('connect')
def handle_connect():
    sid = request.sid
    if num_players == 0 or len(players) >= num_players or sid in players: return
    player_num = len(players)
    players[sid] = player_num
    emit('player_assigned', {'player_num': player_num}, room=sid)
    socketio.emit('waiting_for_players', {'current': len(players), 'needed': num_players})
    if len(players) == num_players:
        start_new_game(is_first_game=True)
        broadcast_game_state(is_start=True)

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in players:
        socketio.emit('player_left', {'player_num': players[request.sid] + 1})
        reset_game()

# app.py 파일에서 이 함수를 찾아 아래 내용으로 완전히 교체해주세요.

@socketio.on('play_hand')
def handle_play_hand(hand_data):
    sid, player_num = request.sid, players.get(request.sid)
    # --- 디버깅 메시지 ---
    print(f"\n--- PLAY HAND by Player {player_num + 1} ---")
    if game_state:
        print(f"PASS LIST before play: {game_state.get('players_who_passed_this_round')}")
    # --------------------

    if player_num is None or not game_state: return
    if player_num != game_state.get('current_player_index'):
        return emit('error_message', {'message': '당신의 턴이 아닙니다.'})
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

    # ✨ 수정된 부분: 패스 기록을 초기화하는 부분이 완전히 삭제되었습니다.
    game_state.update({
        'last_played_hand_info': combo_info,
        'last_played_tiles': submitted_tiles,
        'last_player_to_act_index': player_num
    })
    
    current_hand = game_state['player_hands'][player_num]
    for tile in submitted_tiles:
        if tile in current_hand: current_hand.remove(tile)
    
    # --- 디버깅 메시지 ---
    print(f"PASS LIST after play: {game_state.get('players_who_passed_this_round')}")
    # --------------------
    
    if not current_hand:
        is_game_over = handle_end_of_round(winner_index=player_num)
        if is_game_over:
            final_ranks = get_final_rankings()
            socketio.emit('game_over', final_ranks)
        else:
            start_new_game(is_first_game=False)
            broadcast_game_state(is_start=True)
    else:
        advance_turn()
        print(f"Next turn is now Player {game_state['current_player_index'] + 1}") # 디버깅 메시지
        broadcast_game_state()


@socketio.on('pass_turn')
def handle_pass_turn():
    sid, player_num = request.sid, players.get(request.sid)
    print(f"\n--- PASS TURN by Player {player_num + 1} ---") # 디버깅 메시지
    print(f"PASS LIST before pass: {game_state.get('players_who_passed_this_round')}") # 디버깅 메시지
    
    if player_num is None or not game_state or player_num != game_state['current_player_index'] or game_state['last_played_hand_info'][0] is None or player_num in game_state['players_who_passed_this_round']:
        return

    game_state['players_who_passed_this_round'].append(player_num)
    game_state['game_log'].append(f"P{player_num + 1}: 패스했습니다.")
    print(f"PASS LIST after pass: {game_state.get('players_who_passed_this_round')}") # 디버깅 메시지

    if (num_players - len(game_state['players_who_passed_this_round'])) <= 1:
        game_state.update({'last_played_hand_info': (None, None), 'last_played_tiles': [], 'players_who_passed_this_round': [], 'current_player_index': game_state['last_player_to_act_index']})
        print("New round started by passes. PASS LIST cleared.") # 디버깅 메시지
    else:
        advance_turn()
    
    broadcast_game_state()

@socketio.on('request_new_game')
def on_request_new_game():
    if len(players) > 0: reset_game()

if __name__ == '__main__':
    socketio.run(app, debug=True)
