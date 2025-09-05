import random
from collections import Counter
import functools
import time

# ===================================================================
# 1. Tile 클래스 정의 (렉시오 서열 적용)
# ===================================================================
@functools.total_ordering
class Tile:
    suit_power = {"해": 4, "달": 3, "별": 2, "구름": 1}
    rank_strength = {3: 1, 4: 2, 5: 3, 6: 4, 7: 5, 8: 6, 9: 7, 10: 8, 11: 9, 12: 10, 13: 11, 14: 12, 15: 13, 1: 14, 2: 15}

    def __init__(self, suit, rank):
        self.suit, self.rank = suit, rank
    def __repr__(self):
        return f"({self.suit}, {self.rank})"
    def __eq__(self, other):
        return self.rank == other.rank and self.suit == other.suit
    def __gt__(self, other):
        if self.rank_strength[self.rank] != self.rank_strength[other.rank]:
            return self.rank_strength[self.rank] > self.rank_strength[other.rank]
        return self.suit_power[self.suit] > self.suit_power[other.suit]

# ===================================================================
# 2. 헬퍼 함수 정의
# ===================================================================
def all_ranks_are_same(tiles): return len(set(tile.rank for tile in tiles)) == 1
def ranks_are_sequential(tiles):
    sorted_tiles = sorted(tiles, key=lambda tile: Tile.rank_strength[tile.rank])
    for i in range(len(sorted_tiles) - 1):
        current_strength = Tile.rank_strength[sorted_tiles[i].rank]
        next_strength = Tile.rank_strength[sorted_tiles[i+1].rank]
        if current_strength + 1 != next_strength: return False
    return True
def is_full_house(tiles):
    if len(tiles) != 5: return False
    return sorted(Counter(tile.rank for tile in tiles).values()) == [2, 3]
def all_suits_are_same(tiles): return len(set(tile.suit for tile in tiles)) == 1
def is_four_of_a_kind(tiles):
    if len(tiles) != 5: return False
    return sorted(Counter(tile.rank for tile in tiles).values()) == [1, 4]

combination_ranking = {"싱글": 1, "페어": 2, "트리플": 3, "스트레이트": 4, "플러쉬": 5, "풀하우스": 6, "포카드": 7, "스트레이트 플러쉬": 8}

def get_combination_info(tiles):
    if not tiles: return (None, None)
    num_tiles, highest_tile = len(tiles), max(tiles)
    if num_tiles == 1: return ("싱글", highest_tile)
    if num_tiles == 2 and all_ranks_are_same(tiles): return ("페어", highest_tile)
    if num_tiles == 3 and all_ranks_are_same(tiles): return ("트리플", highest_tile)
    if num_tiles == 5:
        ranks = [t.rank for t in tiles]
        if 1 in ranks and len(set(ranks)) == 5:
            other_four = [t for t in tiles if t.rank != 1]
            strengths = sorted([Tile.rank_strength[t.rank] for t in other_four])
            if len(strengths) == 4 and all(strengths[i] + 1 == strengths[i+1] for i in range(3)):
                is_joker_flush = (len(set(t.suit for t in other_four)) == 1)
                highest_strength = strengths[3] + 1
                strength_to_rank = {v: k for k, v in Tile.rank_strength.items()}
                virtual_rank = strength_to_rank.get(highest_strength)
                if virtual_rank:
                    virtual_rep_tile = Tile(max(tiles).suit, virtual_rank)
                    if is_joker_flush:
                        return ("스트레이트 플러쉬", virtual_rep_tile)
                    else:
                        return ("스트레이트", virtual_rep_tile)

        rank_counts = Counter(rank for rank in ranks)
        counts_values = sorted(rank_counts.values())
        is_straight, is_flush = ranks_are_sequential(tiles), all_suits_are_same(tiles)
        if is_straight and is_flush: return ("스트레이트 플러쉬", highest_tile)
        if counts_values == [1, 4]:
            quad_rank = [r for r, c in rank_counts.items() if c == 4][0]
            rep_tile = max(t for t in tiles if t.rank == quad_rank)
            return ("포카드", rep_tile)
        if counts_values == [2, 3]:
            triple_rank = [r for r, c in rank_counts.items() if c == 3][0]
            rep_tile = max(t for t in tiles if t.rank == triple_rank)
            return ("풀하우스", rep_tile)
        if is_flush:
            sorted_flush_tiles = tuple(sorted(tiles, reverse=True))
            return ("플러쉬", sorted_flush_tiles)
        if is_straight: return ("스트레이트", highest_tile)
    return (None, None)

def is_stronger_combination(new_combo_info, last_combo_info):
    if last_combo_info[0] is None: return True
    new_name, last_name = new_combo_info[0], last_combo_info[0]
    new_tile, last_tile = new_combo_info[1], last_combo_info[1]
    
    if new_name == '플러쉬' and last_name == '플러쉬':
        for i in range(5):
            new_card_strength = Tile.rank_strength[new_tile[i].rank]
            last_card_strength = Tile.rank_strength[last_tile[i].rank]
            if new_card_strength > last_card_strength: return True
            if new_card_strength < last_card_strength: return False
        new_suit_power = Tile.suit_power[new_tile[0].suit]
        last_suit_power = Tile.suit_power[last_tile[0].suit]
        return new_suit_power > last_suit_power
    
    new_rank, last_rank = combination_ranking.get(new_name, 0), combination_ranking.get(last_name, 0)
    if new_rank > last_rank: return True
    if new_rank == last_rank and not isinstance(new_tile, tuple):
        return new_tile > last_tile
    return False

# ===================================================================
# 3. 게임 초기 설정
# ===================================================================
print(">>> Lexio 게임을 시작합니다! <<<")
while True:
    try:
        num_players_input = input('인원수를 입력해 주세요 (3~5명): ')
        num_players = int(num_players_input)
        if 3 <= num_players <= 5: break
        else: print(">>> 오류: 3, 4, 5 중 하나를 입력해주세요.")
    except ValueError:
        print(">>> 오류: 숫자를 정확하게 입력해주세요.")

if num_players == 3: tiles_per_player = 15
elif num_players == 4: tiles_per_player = 13
elif num_players == 5: tiles_per_player = 12

player_money = [27] * num_players
round_number = 1

# ===================================================================
# 4. 메인 게임 세션 루프
# ===================================================================
while True:
    print("\n" + "#"*60)
    print(f"# 라운드 {round_number} 시작!")
    print("#"*60)
    time.sleep(1)

    suits, ranks = ["구름", "별", "달", "해"], list(range(1, 16))
    deck = [Tile(suit, rank) for suit in suits for rank in ranks]
    random.shuffle(deck)
    player_hands = [[] for _ in range(num_players)]
    for _ in range(tiles_per_player):
        for i in range(num_players):
            player_hands[i].append(deck.pop())
    for hand in player_hands:
        hand.sort()

    starting_tile = Tile("구름", 3)
    start_player_found = False
    for i, hand in enumerate(player_hands):
        if starting_tile in hand:
            current_player_index = i
            start_player_found = True
            print(f"\n>>> 가장 약한 패인 {starting_tile}를 가진 플레이어 {i+1}부터 시작합니다. <<<")
            break
    if not start_player_found:
        current_player_index = 0
        print(f"\n>>> '구름 3'을 가진 플레이어가 없어 플레이어 1부터 시작합니다. <<<")

    last_played_hand_info = (None, None)
    last_player_to_act_index = -1
    players_who_passed_this_round = []
    round_over = False

    while not round_over:
        if current_player_index in players_who_passed_this_round:
            current_player_index = (current_player_index + 1) % num_players
            continue
        
        active_players_count = num_players - len(players_who_passed_this_round)
        if active_players_count == 1 and last_played_hand_info[0] is not None:
            print("\n--- 다른 모든 플레이어가 패스했습니다. 새로운 라운드를 시작합니다. ---")
            last_played_hand_info = (None, None)
            players_who_passed_this_round.clear() 
            current_player_index = last_player_to_act_index 
            continue

        current_hand = player_hands[current_player_index]
        
        print("\n" + "="*50)
        print(f"플레이어 {current_player_index + 1}의 턴 (보유 금액: {player_money[current_player_index]}원)")
        print(f"현재 나온 패: {last_played_hand_info[0]} / ", end="")
        if isinstance(last_played_hand_info[1], tuple):
            print(last_played_hand_info[1][0] if last_played_hand_info[1] else "")
        else:
            print(last_played_hand_info[1])
        hand_display = " ".join([f"{i}:{tile}" for i, tile in enumerate(current_hand)])
        print("당신의 패:", hand_display)
        
        action = input("낼 타일의 번호를 띄어쓰기로 입력하세요 (예: 0 3 5). 패스하려면 'p'를 입력하세요: ").strip().lower()

        if action == 'p':
            if last_played_hand_info[0] is None:
                print(">>> 라운드의 선두는 패스할 수 없습니다. 패를 내주세요.")
                time.sleep(1)
                continue
            print(f"플레이어 {current_player_index + 1} (이)가 패스했습니다.")
            players_who_passed_this_round.append(current_player_index)
            current_player_index = (current_player_index + 1) % num_players
            continue

        try:
            indices = sorted([int(i) for i in action.split()], reverse=True)
            submitted_tiles = [current_hand[i] for i in indices]
            submitted_combo_info = get_combination_info(submitted_tiles)
            
            if submitted_combo_info[0] is None:
                print(">>> 잘못된 조합입니다. 다시 시도하세요.")
                continue
            
            if not is_stronger_combination(submitted_combo_info, last_played_hand_info):
                print(">>> 더 약한 패이거나 규칙에 맞지 않는 패입니다. 다시 시도하세요.")
                continue
                
            print(f">>> {submitted_combo_info[0]}을(를) 냈습니다: {submitted_tiles}")
            last_played_hand_info = submitted_combo_info
            last_player_to_act_index = current_player_index
            
            for i in indices:
                current_hand.pop(i)

            if not current_hand:
                round_winner_index = current_player_index
                print("\n" + "*"*50)
                print(f"🎉 플레이어 {round_winner_index + 1}님이 이번 라운드에서 승리했습니다! 🎉")
                print("*"*50)
                round_over = True
            else:
                current_player_index = (current_player_index + 1) % num_players

        except (ValueError, IndexError):
            print(">>> 잘못된 입력입니다. 숫자를 정확하게 입력해주세요.")

    # --- 4.4. 라운드 종료 및 점수 정산 ---
    print("\n" + "="*50)
    print(f"라운드 {round_number} 종료! 점수를 정산합니다.")
    print("="*50)
    final_card_counts = [len(hand) for hand in player_hands]
    print(f"라운드 종료 시 카드 수: {final_card_counts}")
    time.sleep(1)

    for i in range(num_players):
        for j in range(num_players):
            if i == j: continue
            if final_card_counts[j] > final_card_counts[i]:
                payment = final_card_counts[j] - final_card_counts[i]
                player_money[i] += payment
                player_money[j] -= payment
                print(f"플레이어 {j + 1} → 플레이어 {i + 1}에게 {payment}원 지불")
                time.sleep(0.5)

    print("\n" + "="*50)
    print("현재 보유 금액")
    print("="*50)
    for i, money in enumerate(player_money):
        print(f"플레이어 {i + 1}: {money}원")

    # --- 4.5. 파산 확인 및 게임 최종 종료 ---
    is_bankrupt = False
    for i, money in enumerate(player_money):
        if money <= 0:
            print(f"\n### 플레이어 {i + 1}님이 파산하여 게임이 곧 종료됩니다. ###")
            is_bankrupt = True
    
    if is_bankrupt:
        break
    
    round_number += 1

# ===================================================================
# 7. 최종 순위 발표
# ===================================================================
print("\n" + "#"*60)
print("# 게임 최종 결과")
print("#"*60)
time.sleep(1)

survivors = []
bankrupt_players = []

for i, money in enumerate(player_money):
    if money > 0:
        survivors.append((money, i + 1))
    else:
        bankrupt_players.append(i + 1)

survivors.sort(reverse=True)

print("### 최종 순위 ###")
for rank, (money, player_num) in enumerate(survivors):
    print(f"{rank + 1}등: 플레이어 {player_num} (최종 금액: {money}원)")

if bankrupt_players:
    bankrupt_str_list = [str(p) for p in bankrupt_players]
    print(f"파산: 플레이어 {', '.join(bankrupt_str_list)}")