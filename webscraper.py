import argparse
import json
import re
import math

import bs4
import requests
from bs4 import BeautifulSoup

import properties

PLAYER_DICT = {}

def load_players():
    response = requests.get("https://3vxcifd2rc.execute-api.us-west-2.amazonaws.com/PROD/players", headers = {"Token": properties.TOKEN})
    for player in response.json():
        PLAYER_DICT[player["name"]] = player["player_id"]

def generate_tourney(url):
    round = scrape(url)
    rounds = generate_empty_rounds(round)
    tournament = {"rounds": rounds}
    json_tournament = json.dumps(tournament, indent = 4, sort_keys = True)
    with open("tournament.json", "w") as f:
        f.write(json_tournament)

def scrape(url):
    response = requests.get(url)
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
        match_info = MatchInfo(round, i + 1, player1_name, player1_seed, player2_name, player2_seed)
        match_info_list.append(match_info.__dict__)
    return match_info_list

def prompt_tourney():
    round = []
    position = 1
    seed_pattern = re.compile("\((\d+)\)$")
    while True:
        player1 = input("Player 1: ")
        if player1 == "quit":
            break
        player2 = input("Player 2: ")
        player1_name, seed1 = split(seed_pattern, player1)
        player2_name, seed2 = split(seed_pattern, player2)
        round.append(MatchInfo(1, position, player1_name, seed1, player2_name, seed2).__dict__)
        position += 1
    rounds = generate_empty_rounds(round)
    print(json.dumps({"rounds": rounds}, indent = 4, sort_keys = True))

def generate_empty_rounds(round):
    match_count = len(round)
    rounds = [round]
    total_rounds = int(math.log(match_count, 2))
    for current_round in range(1, total_rounds + 1):
        match_list = []
        total_matches = int(match_count / math.pow(2, current_round))
        for match_number in range(total_matches):
            match_list.append(MatchInfo(current_round + 1, match_number + 1).__dict__)
        rounds.append(match_list)
    return rounds

def get_seed(row):
    return re.sub(r"\D", "", row.find("span").string) if row.find("span") else None

def get_name(row):
    link = row.find("a", "scores-draw-entry-box-players-item")
    return link['data-ga-label'] if link is not None else None

def split(pattern, player):
    match = pattern.search(player)
    if match is None:
        return player, None
    else:
        return player[:match.start()].strip(), match.group(1)

class MatchInfo:
    def __init__(self, round, position, player1_name = None, seed1 = None, player2_name = None, seed2 = None):
        self.round = round
        self.position = position
        if player1_name is not None and player1_name != "":
            player1_id = self.find_id(player1_name)
            if player1_id is not None:
                self.player1_id = player1_id
            else:
                self.player1_name = player1_name
        if seed1 is not None and seed1 != "":
            self.seed1 = int(seed1)
        if player2_name is not None and player2_name != "":
            player2_id = self.find_id(player2_name)
            if player2_id is not None:
                self.player2_id = player2_id
            else:
                self.player2_name = player2_name
        if seed2 is not None and seed2 != "":
            self.seed2 = int(seed2)

    @staticmethod
    def find_id(player_name):
        return PLAYER_DICT[player_name] if player_name in PLAYER_DICT else None

parser = argparse.ArgumentParser()
parser.add_argument("-u", "--url")
args = parser.parse_args()

load_players()
if args.url is not None:
    generate_tourney(args.url)
else:
    prompt_tourney()
