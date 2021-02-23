# -*- coding: utf-8 -*-
import asyncio
import datetime
import math
import subprocess
from calendar import monthrange

import aiohttp
from bs4 import BeautifulSoup
from solid import *
from solid.utils import *
import numpy as np


__author__ = "Félix Gómez"


def gitlab_skyline(username, year, domain, max_requests):
    contribution_matrix = []
    print("Fetching contributions from Gitlab...")

    semaphore = asyncio.Semaphore(max_requests)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        asyncio.wait(
            [get_contributions(semaphore, domain, username, date, contribution_matrix) for date in
             all_dates_in_year(year)]))
    loop.close()

    print("Generating STL...")
    generate_skyline_stl(username, year, contribution_matrix)


async def get_contributions(semaphore, domain, username, date, contribution_matrix):
    """Get contributions directly using Gitlab activities endpoint API (asynchronously)"""
    async with aiohttp.ClientSession(raise_for_status=True) as client:
        try:
            date_as_str = date.strftime("%Y-%m-%d")
            url = domain + '/users/' + username + '/calendar_activities?date=' + date_as_str
            async with semaphore, client.get(url) as response:
                content = await response.text()
                soup = BeautifulSoup(content, 'html.parser')
                contribution_matrix.append(
                    [int(date.strftime('%j')), int(date.strftime('%u')) - 1, len(soup.find_all('li'))])

        except Exception as err:
            print(f"Exception occured: {err}")
            pass


def all_dates_in_year(year=2020):
    for month in range(1, 13):
        for day in range(1, monthrange(year, month)[1] + 1):
            yield datetime.datetime(year, month, day)


def parse_contribution_matrix(contribution_matrix):
    np_contribution_matrix = np.array(contribution_matrix)

    np_contribution_matrix.view('i8,i8,i8').sort(order=['f0'], axis=0)
    *_, max_contributions_by_day = np_contribution_matrix.max(axis=0)
    day_offset = np_contribution_matrix[0][1]
    year_contribution_list = np.delete(np_contribution_matrix, (0, 1), 1).flatten().tolist()

    for i in range(day_offset):
        year_contribution_list.insert(0, 0)

    return [year_contribution_list, max_contributions_by_day]


def generate_skyline_stl(username, year, contribution_matrix):
    year_contribution_list, max_contributions_by_day = parse_contribution_matrix(contribution_matrix)

    base_top_width = 18
    base_width = 25
    base_length = 125
    base_height = 10
    max_length_contributionbar = 20

    base_top_offset = (base_width - base_top_width) / 2
    face_angle = math.degrees(math.atan(base_height / base_top_offset))

    base_points = [
        [0, 0, 0],
        [base_length, 0, 0],
        [base_length, base_width, 0],
        [0, base_width, 0],
        [base_top_offset, base_top_offset, base_height],
        [base_length - base_top_offset, base_top_offset, base_height],
        [base_length - base_top_offset, base_width - base_top_offset, base_height],
        [base_top_offset, base_width - base_top_offset, base_height]
    ]

    base_faces = [
        [0, 1, 2, 3],  # bottom
        [4, 5, 1, 0],  # front
        [7, 6, 5, 4],  # top
        [5, 6, 2, 1],  # right
        [6, 7, 3, 2],  # back
        [7, 4, 0, 3]  # left
    ]

    base_scad = polyhedron(points=base_points, faces=base_faces)

    year_scad = rotate([face_angle, 0, 0])(
        translate([base_length - base_length / 5, base_height / 2 - base_top_offset / 2, -1])(
            linear_extrude(height=2)(
                text(str(year), 5)
            )
        )
    )

    user_scad = rotate([face_angle, 0, 0])(
        translate([base_length / 4, base_height / 2 - base_top_offset / 2, -1])(
            linear_extrude(height=2)(
                text("@" + username, 4)
            )
        )
    )

    logo_gitlab_scad = rotate([face_angle, 0, 0])(
        translate([base_length / 8, base_height / 2 - base_top_offset / 2 - 2, -1])(
            linear_extrude(height=2)(
                scale([0.09, 0.09, 0.09])(
                    import_stl("gitlab.svg")
                )
            )
        )
    )

    bars = None

    week_number = 1
    for i in range(len(year_contribution_list)):

        day_number = i % 7
        if day_number == 0:
            week_number += 1

        if year_contribution_list[i] == 0:
            continue

        bar = translate(
            [base_top_offset + 2 + week_number * 2, base_top_offset + 2 + day_number * 2, base_height])(
            cube([2, 2, year_contribution_list[i] * max_length_contributionbar / max_contributions_by_day])
        )

        if bars is None:
            bars = bar
        else:
            bars += bar

    scad_contributions_filename = 'gitlab_' + username + '_' + str(year)
    scad_skyline_object = base_scad - logo_gitlab_scad + user_scad + year_scad

    if bars is not None:
        scad_skyline_object += bars

    scad_render_to_file(scad_skyline_object,
                        scad_contributions_filename + '.scad')

    subprocess.run(['openscad', '-o', scad_contributions_filename + '.stl', scad_contributions_filename + '.scad'],
                   capture_output=True)

    print('Generated STL file ' + scad_contributions_filename +
          '.stl')