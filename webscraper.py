from bs4 import BeautifulSoup
import bs4
import json
import requests
import re
import sys

import properties

def load_players():
    response = requests.get("https://3vxcifd2rc.execute-api.us-west-2.amazonaws.com/PROD/players", headers = {"Token": properties.TOKEN})
    player_list = {}
    for player in response.json():
        player_list[player["name"]] = player["player_id"]
    return player_list

def generate_tourney():
    player_list = load_players()
    round1 = scrape(player_list)
    match_count = len(round1)
    rounds = [round1]
    round = 2
    while match_count >= 1:
        match_count //= 2
        rounds.append(generate_empty_round(round, match_count))
        round += 1
    tournament = {"rounds": rounds}
    json_tournament = json.dumps(tournament, indent = 4, sort_keys = True)
    with open("tournament.json", "w") as f:
        f.write(json_tournament)

def scrape(player_list):
    response = requests.get(sys.argv[1])
    soup = BeautifulSoup(response.text, "lxml")
    table = soup.find("table", id = "scoresDrawTable")
    round_one_matches = []
    for row in list(table.tbody.children):
        if isinstance(row, bs4.element.Tag):
            round_one_matches.append(row)
    round = 1
    match_info_list = []
    for i in range(len(round_one_matches)):
        match = round_one_matches[i]
        match_rows = match.find_all("tr")
        player1_seed = get_seed(match_rows[0])
        player1_name = get_name(match_rows[0])
        player2_seed = get_seed(match_rows[1])
        player2_name = get_name(match_rows[1])
        match_info = MatchInfo(round, i + 1, player1_name, player1_seed, player2_name, player2_seed, player_list)
        match_info_list.append(match_info.__dict__)
    return match_info_list

def get_seed(row):
    return re.sub(r"\D", "", row.find("span").string) if row.find("span") else None

def get_name(row):
    return row.find("a", class_ = "scores-draw-entry-box-players-item")['data-ga-label'] if row.find("a", "scores-draw-entry-box-players-item") else None

def find_id(player_list, player_name):
    return player_list[player_name] if player_name is not None else None

def generate_empty_round(round_number, match_count):
    match_list = []
    for match_number in range(1, match_count + 1):
        match_list.append(MatchInfo(round_number, match_number, None, None, None, None, None).__dict__)
    return match_list

class MatchInfo:
    def __init__(self, round, position, player1_name, seed1, player2_name, seed2, player_list):
        self.round = round
        self.position = position
        if player1_name is not None:
            self.player1_id = (player_list[player1_name] if player1_name in player_list else player1_name)
        if seed1 is not None and seed1 != "":
            self.seed1 = int(seed1)
        if player2_name is not None:
            self.player2_id = (player_list[player2_name] if player2_name in player_list else player2_name)
        if seed2 is not None and seed2 != "":
            self.seed2 = int(seed2)

generate_tourney()
