#!/usr/local/bin/python3

import argparse
import json
import re
import math

import bs4
import requests
from bs4 import BeautifulSoup

import properties

BASE_URL = "https://3vxcifd2rc.execute-api.us-west-2.amazonaws.com/PROD/{}"
HEADERS = {"Token": properties.TOKEN}

PLAYER_DICT = {}
for player in requests.get(BASE_URL.format("players"), headers = HEADERS).json():
    PLAYER_DICT[player["name"]] = player["player_id"]

def scrape_bracket(url, test_html_filename = None):
    soup = BeautifulSoup(requests.get(url).text if test_html_filename is None else open(test_html_filename).read(), "lxml")
    table = soup.find("table", id = "scoresDrawTable")

    seeds = {}
    rounds = [[] for _ in table.thead.tr.find_all("th")]
    for row in list([row for row in table.tbody.children if isinstance(row, bs4.element.Tag)]):
        for round, round_td in enumerate([td for td in list(row.children) if isinstance(td, bs4.element.Tag)]):
            if round == 0:
                match_trs = round_td.find_all("tr")
                player1_name = get_name(match_trs[0])
                player2_name = get_name(match_trs[1])
                rounds[round] += [player1_name, player2_name]

                seeds[player1_name] = get_seed(match_trs[0])
                seeds[player2_name] = get_seed(match_trs[1])
            else:
                player_name = get_name(round_td)
                rounds[round].append(player_name)

    bracket = []
    for round, players in enumerate(rounds[:-1]):
        bracket.append([])
        for i in range(0, len(players), 2):
            player1, player2 = players[i], players[i + 1]
            seed1, seed2 = seeds[player1] if player1 in seeds else None, seeds[player2] if player2 in seeds else None
            winner_name = rounds[round + 1][int(i / 2)]
            match = Match(round + 1, int(i / 2) + 1, player1, player2, seed1, seed2, winner_name)
            bracket[round].append(match.__dict__)
    return {"rounds": bracket}

def get_seed(tag):
    return re.sub(r"\D", "", tag.find("span").string) if tag.find("span") else None

def get_name(tag):
    link = tag.find("a", "scores-draw-entry-box-players-item")
    return link['data-ga-label'] if link is not None else None

class Match:
    def __init__(self, round, position, player1_name = None, player2_name = None, seed1 = None, seed2 = None, winner_name = None):
        self.round = round
        self.position = position
        self.set_player_info(player1_name, seed1, "1")
        self.set_player_info(player2_name, seed2, "2")
        winner_id = self.find_id(winner_name)
        if winner_id is not None:
            self.winner_id = winner_id

    def set_player_info(self, name, seed, position):
        if name is not None and name != "":
            id = self.find_id(name)
            if id is not None:
                setattr(self, "player{}_id".format(position), id)
            else:
                setattr(self, "player{}_name".format(position), name)
        if seed is not None and seed != "":
            setattr(self, "seed{}".format(position), seed)

    @staticmethod
    def find_id(player_name):
        return PLAYER_DICT[player_name] if player_name in PLAYER_DICT else None


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--tournament_id", required = True)
    args = parser.parse_args()

    response = requests.get(BASE_URL.format("tournaments/{}".format(args.tournament_id)), headers = HEADERS)
    assert response.status_code == 200
    tournament = response.json()

    draws_url = tournament.get("draws_url")
    if draws_url is None:
        print("Tournament does not have a draws_url yet. Unable to update.")
        exit()

    bracket = scrape_bracket(draws_url)

    master_bracket_id = tournament.get("master_bracket_id")
    if master_bracket_id is not None:
        # Get the master bracket
        response = requests.get(BASE_URL.format("tournaments/{}/brackets/{}".format(args.tournament_id, master_bracket_id)), headers = HEADERS)
        assert response.status_code == 200
        master_bracket = response.json()

        # Update the master bracket
        master_bracket["rounds"] = bracket["rounds"]
        response = requests.put(BASE_URL.format("tournaments/{}/brackets/{}".format(args.tournament_id, tournament["master_bracket_id"])), headers = HEADERS, json = master_bracket)
        print(response.status_code, response.text)
    else:
        # Create the master bracket
        response = requests.post(BASE_URL.format("tournaments/{}/brackets".format(args.tournament_id)), headers = HEADERS, json = bracket)
        print(response.status_code, response.text)
