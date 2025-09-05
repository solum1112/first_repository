# game_logic.py
import functools
from collections import Counter

# ===================================================================
# 게임 엔진: Tile 클래스 및 헬퍼 함수
# ===================================================================
@functools.total_ordering
class Tile:
    suit_power = {"sun": 4, "moon": 3, "star": 2, "cloud": 1}
    rank_strength = {3: 1, 4: 2, 5: 3, 6: 4, 7: 5, 8: 6, 9: 7, 10: 8, 11: 9, 12: 10, 13: 11, 14: 12, 15: 13, 1: 14, 2: 15}
    def __init__(self, suit, rank): self.suit, self.rank = suit, rank
    def __repr__(self): return f"({self.suit}, {self.rank})"
    def to_dict(self): return {'suit': self.suit, 'rank': self.rank}
    def __eq__(self, other): return self.rank == other.rank and self.suit == other.suit
    def __gt__(self, other):
        if self.rank_strength[self.rank] != self.rank_strength[other.rank]: return self.rank_strength[self.rank] > self.rank_strength[other.rank]
        return self.suit_power[self.suit] > self.suit_power[other.suit]

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
                    if is_joker_flush: return ("스트레이트 플러쉬", virtual_rep_tile)
                    else: return ("스트레이트", virtual_rep_tile)
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
    if new_rank == last_rank and not isinstance(new_tile, tuple): return new_tile > last_tile
    return False