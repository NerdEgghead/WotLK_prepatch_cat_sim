#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Run this app with `python app.py` and
# visit http://127.0.0.1:8050/ in your web browser.

import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objects as go
import numpy as np
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
import prepatch_cat_sim as ccs
import multiprocessing
import trinkets
import copy
import json
import base64
import io


app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])
server = app.server

default_input_stats = {
        "agility": 747,
        "armor": 4455,
        "armorPen": 27.92,
        "armorPenRating": 188,
        "attackPower": 4279,
        "crit": 44.22,
        "critRating": 156,
        "critReduction": 6,
        "defense": 350,
        "dodge": 43.09,
        "expertise": 16,
        "expertiseRating": 27,
        "feralAttackPower": 1195,
        "haste": 5.44,
        "hasteRating": 66,
        "health": 9854,
        "hit": 8.94,
        "hitRating": 141,
        "intellect": 252,
        "mainHandSpeed": 3,
        "mana": 5870,
        "natureResist": 10,
        "parry": 5,
        "spellCrit": 12.07,
        "spellHaste": 5.44,
        "spellHit": 11.18,
        "spirit": 158,
        "stamina": 642,
        "strength": 263
}

stat_input = dbc.Col([
    html.H5('Eighty Upgrades Input'),
    dcc.Markdown(
        'This simulator uses Eighty Upgrades as its gear selection UI. In '
        'order to use it, create a Eighty Upgrades profile for your character'
        ' and download the gear set using the "Export" button at the top right'
        ' of the character sheet. Make sure that "Cat Form" is selected in the'
        ' export window, and that "Talents" are checked (and set up in your '
        'character sheet). Also make sure that trinket and Idol slots are left'
        ' empty prior to exporting, as these will be selected in the sim UI.',
        style={'width': 300},
    ),
    dcc.Markdown(
        'Consumables and party/raid buffs can be specified either in the '
        'Eighty Upgrades "Buffs" tab, or in the "Consumables" and "Raid '
        'Buffs " sections in the sim. If the "Buffs" option is checked in the '
        'Eighty Upgrades export window, then the corresponding sections in '
        'the sim input will be ignored.',
        style={'width': 300},
    ),
    dcc.Upload(
        id='upload-data',
        children=html.Div([
            'Drag and Drop or ',
            html.A('Select File')
        ]),
        style={
            'width': '100%',
            'height': '60px',
            'lineHeight': '60px',
            'borderWidth': '1px',
            'borderStyle': 'dashed',
            'borderRadius': '5px',
            'textAlign': 'center',
            'margin': '0px'
        },
        # Don't allow multiple files to be uploaded
        multiple=False
    ),
    html.Br(),
    html.Div(
        'No file uploaded, using default input stats instead.',
        id='upload_status', style={'color': '#E59F3A'}
    ),
    html.Br(),
    html.H5('Idols and Set Bonuses'),
    dbc.Checklist(
        options=[{'label': 'Idol of the Raven Goddess', 'value': 'raven'}],
        value=['raven'], id='raven_idol'
    ),
    dbc.Checklist(
        options=[
            {'label': 'Everbloom Idol', 'value': 'everbloom'},
            {'label': 'Idol of Terror', 'value': 'idol_of_terror'},
            {'label': 'Idol of the White Stag', 'value': 'stag_idol'},
            {'label': '2-piece Tier 4 bonus', 'value': 't4_bonus'},
            {'label': '4-piece Tier 5 bonus', 'value': 't5_bonus'},
            {'label': '2-piece Tier 6 bonus', 'value': 't6_2p'},
            {'label': '4-piece Tier 6 bonus', 'value': 't6_4p'},
            {'label': 'Wolfshead Helm', 'value': 'wolfshead'},
            {'label': 'Relentless Earthstorm Diamond', 'value': 'meta'},
            {'label': 'Band of the Eternal Champion', 'value': 'exalted_ring'},
            {'label': 'Enchant Weapon: Mongoose', 'value': 'mongoose'},
        ],
        value=['t6_2p', 't6_4p', 'meta', 'mongoose'],
        id='bonuses'
    ),
    ], width='auto', style={'marginBottom': '2.5%', 'marginLeft': '2.5%'})

buffs_1 = dbc.Col(
    [dbc.Collapse([html.H5('Consumables'),
     dbc.Checklist(
         options=[{'label': 'Elixir of Major Agility', 'value': 'agi_elixir'},
                  {'label': 'Elixir of Draenic Wisdom', 'value': 'draenic'},
                  {'label': 'Warp Burger / Grilled Mudfish', 'value': 'food'},
                  {'label': 'Adamantite Weightstone', 'value': 'weightstone'}],
         value=[
             'agi_elixir', 'food', 'weightstone',
         ],
         id='consumables'
     ),
     html.Br(),
     html.H5('Raid Buffs'),
     dbc.Checklist(
         options=[{'label': 'Blessing of Kings', 'value': 'kings'},
                  {
                      'label': 'Blessing of Might / Battle Shout',
                      'value': 'might'
                  },
                  {
                      'label': 'Blessing of Wisdom / Mana Spring Totem',
                      'value': 'wisdom'
                  },
                  {'label': 'Mark of the Wild', 'value': 'motw'},
                  {'label': 'Heroic Presence', 'value': 'heroic_presence'},
                  {
                      'label': 'Strength of Earth Totem / Horn of Winter',
                      'value': 'str_totem'
                  },
                  {
                      'label': "Unleashed Rage / Trueshot Aura / Abomination's Might",
                      'value': 'unleashed_rage'
                  },
                  {'label': 'Arcane Intellect', 'value': 'ai'},
                  {'label': 'Prayer of Spirit', 'value': 'spirit'}],
         value=[
             'kings', 'might', 'wisdom', 'motw', 'str_totem', 'unleashed_rage',
             'ai'
         ],
         id='raid_buffs'
     ),
     html.Br()], id='buff_section', is_open=True),
     html.H5('Other Buffs'),
     dbc.Checklist(
         options=[
             {
                 'label': 'Sanctified Retribution / Ferocious Inspiration / Arcane Empowerment',
                 'value': 'sanc_aura'
             },
             {'label': 'Braided Eternium Chain', 'value': 'be_chain'},
             {
                 'label': 'Improved Windfury Totem / Improved Icy Talons',
                 'value': 'major_haste'
             },
             {
                 'label': 'Improved Moonkin Form / Swift Retribution',
                 'value': 'minor_haste'
             },
         ],
         value=['sanc_aura', 'major_haste', 'minor_haste'], id='other_buffs'
     )],
    width='auto', style={'marginBottom': '2.5%', 'marginLeft': '2.5%'}
)

encounter_details = dbc.Col(
    [html.H4('Encounter Details'),
     dbc.InputGroup(
         [
             dbc.InputGroupAddon('Fight Length:', addon_type='prepend'),
             dbc.Input(
                 value=120.0, type='number', id='fight_length',
             ),
             dbc.InputGroupAddon('seconds', addon_type='append')
         ],
         style={'width': '75%'}
     ),
     dbc.InputGroup(
         [
             dbc.InputGroupAddon('Boss Armor:', addon_type='prepend'),
             dbc.Input(value=6193, type='number', id='boss_armor')
         ],
         style={'width': '50%'}
     ),
     html.Br(),
     html.H5('Damage Debuffs'),
     dbc.Checklist(
         options=[
             {'label': 'Gift of Arthas', 'value': 'gift_of_arthas'},
             {'label': 'Sunder Armor', 'value': 'sunder'},
             {'label': 'Faerie Fire', 'value': 'faerie_fire'},
             {
                 'label': 'Blood Frenzy / Savage Combat',
                 'value': 'blood_frenzy'
             },
         ],
         value=['gift_of_arthas', 'sunder', 'faerie_fire', 'blood_frenzy'],
         id='boss_debuffs'
     ),
     html.Br(),
     html.H5('Stat Debuffs'),
     dbc.Checklist(
         options=[
             {
                 'label': 'Heart of the Crusader / Master Poisoner',
                 'value': 'jotc'
             },
             {'label': 'Judgment of Wisdom', 'value': 'jow'},
         ],
         value=['jotc', 'jow'],
         id='stat_debuffs',
     ),
     html.Br(),
     html.H5('Cooldowns'),
     dbc.Checklist(
         options=[
             {'label': 'Bloodlust', 'value': 'lust'},
             {'label': 'Drums of Battle', 'value': 'drums'},
             {'label': 'Dark / Demonic Rune', 'value': 'rune'},
         ],
         value=['lust', 'drums', 'rune'], id='cooldowns',
     ),
     dbc.InputGroup(
         [
             dbc.InputGroupAddon('Potion CD:', addon_type='prepend'),
             dbc.Select(
                 options=[
                     {'label': 'Super Mana Potion', 'value': 'super'},
                     {'label': 'Fel Mana Potion', 'value': 'fel'},
                     {'label': 'Haste Potion', 'value': 'haste'},
                     {'label': 'None', 'value': 'none'},
                 ],
                 value='haste', id='potion',
             ),
         ],
         style={'width': '75%', 'marginTop': '1.5%'}
     )],
    width='auto',
    style={
        'marginLeft': '2.5%', 'marginBottom': '2.5%', 'marginRight': '-2.5%'
    }
)

# Sim replicates input
iteration_input = dbc.Col([
    html.H4('Sim Settings'),
    dbc.InputGroup(
        [
            dbc.InputGroupAddon('Number of replicates:', addon_type='prepend'),
            dbc.Input(value=20000, type='number', id='num_replicates')
        ],
        style={'width': '50%'}
    ),
    dbc.InputGroup(
        [
            dbc.InputGroupAddon('Modeled input delay:', addon_type='prepend'),
            dbc.Input(
                value=100, type='number', id='latency', min=1, step=1,
            ),
            dbc.InputGroupAddon('ms', addon_type='append')
        ],
        style={'width': '50%'}
    ),
    html.Br(),
    html.H5('Talents'),
    dbc.Checklist(
        options=[
            {'label': 'Omen of Clarity', 'value': 'omen'},
            {'label': 'Berserk', 'value': 'berserk'},
            {'label': 'Primal Gore', 'value': 'primal_gore'},
        ],
        value=['berserk', 'primal_gore'], id='binary_talents'
    ),
    html.Br(),
    html.Div([
        html.Div(
            'Feral Aggression:',
            style={
                'width': '35%', 'display': 'inline-block',
                'fontWeight': 'bold'
            }
        ),
        dbc.Select(
            options=[
                {'label': '0', 'value': 0},
                {'label': '1', 'value': 1},
                {'label': '2', 'value': 2},
                {'label': '3', 'value': 3},
                {'label': '4', 'value': 4},
                {'label': '5', 'value': 5},
            ],
            value=5, id='feral_aggression',
            style={
                'width': '20%', 'display': 'inline-block',
                'marginBottom': '2.5%', 'marginRight': '5%'
            }
        )]),
    html.Div([
        html.Div(
            'Savage Fury:',
            style={
                'width': '35%', 'display': 'inline-block',
                'fontWeight': 'bold'
            }
        ),
        dbc.Select(
            options=[
                {'label': '0', 'value': 0},
                {'label': '1', 'value': 1},
                {'label': '2', 'value': 2},
            ],
            value=2, id='savage_fury',
            style={
                'width': '20%', 'display': 'inline-block',
                'marginBottom': '2.5%', 'marginRight': '5%'
            }
        )]),
    html.Div([
        html.Div(
            'Naturalist:',
            style={
                'width': '35%', 'display': 'inline-block',
                'fontWeight': 'bold'
            }
        ),
        dbc.Select(
            options=[
                {'label': '0', 'value': 0},
                {'label': '1', 'value': 1},
                {'label': '2', 'value': 2},
                {'label': '3', 'value': 3},
                {'label': '4', 'value': 4},
                {'label': '5', 'value': 5},
            ],
            value=4, id='naturalist',
            style={
                'width': '20%', 'display': 'inline-block',
                'marginBottom': '2.5%', 'marginRight': '5%'
            }
        )]),
    html.Div([
        html.Div(
            'Natural Shapeshifter:',
            style={
                'width': '35%', 'display': 'inline-block',
                'fontWeight': 'bold'
            }
        ),
        dbc.Select(
            options=[
                {'label': '0', 'value': 0},
                {'label': '1', 'value': 1},
                {'label': '2', 'value': 2},
                {'label': '3', 'value': 3},
            ],
            value='0', id='natural_shapeshifter',
            style={
                'width': '20%', 'display': 'inline-block',
                'marginBottom': '2.5%', 'marginRight': '5%'
            }
        )]),
    html.Div([
        html.Div(
            'Intensity:',
            style={
                'width': '35%', 'display': 'inline-block',
                'fontWeight': 'bold'
            }
        ),
        dbc.Select(
            options=[
                {'label': '0', 'value': 0},
                {'label': '1', 'value': 1},
                {'label': '2', 'value': 2},
                {'label': '3', 'value': 3},
            ],
            value='0', id='intensity',
            style={
                'width': '20%', 'display': 'inline-block',
                'marginBottom': '2.5%', 'marginRight': '5%'
            }
        )]),
    html.Br(),
    html.H5('Player Strategy'),
    dbc.InputGroup(
        [
            dbc.InputGroupAddon(
                'Minimum combo points for Rip:', addon_type='prepend'
            ),
            dbc.Select(
                options=[
                    {'label': '3', 'value': 3},
                    {'label': '4', 'value': 4},
                    {'label': '5', 'value': 5},
                ],
                value=5, id='rip_cp',
            ),
        ],
        style={'width': '48%', 'marginBottom': '1.5%'}
    ),
    dbc.InputGroup(
        [
            dbc.InputGroupAddon(
                'Minimum combo points for Ferocious Bite:',
                addon_type='prepend'
            ),
            dbc.Select(
                options=[
                    {'label': '3', 'value': 3},
                    {'label': '4', 'value': 4},
                    {'label': '5', 'value': 5},
                ],
                value=5, id='bite_cp',
            ),
        ],
        style={'width': '60%', 'marginBottom': '1.5%'}
    ),
    dbc.InputGroup(
        [
            dbc.InputGroupAddon('Wait', addon_type='prepend'),
            dbc.Input(
                value=0.0, min=0.0, step=0.5, type='number', id='cd_delay',
            ),
            dbc.InputGroupAddon(
                'seconds before using cooldowns', addon_type='append'
            ),
        ],
        style={'width': '63%'},
    ),
    html.Br(),
    dbc.Row([
        dbc.Col(dbc.Checklist(
            options=[{'label': " weave Ferocious Bite", 'value': 'bite'}],
            value=['bite'], id='use_biteweave',
        ), width='auto'),
        dbc.Col('with', width='auto', id='biteweave_text_1'),
        dbc.Col(dbc.Input(
            type='number', value=5, id='bite_time', min=0.0, step=0.1,
            style={'marginTop': '-3%', 'marginBottom': '7%', 'width': '40%'},
        ), width='auto'),
        dbc.Col(
            'seconds left on Rip', width='auto', style={'marginLeft': '-15%'},
            id='biteweave_text_2'
        )
    ],),
    dbc.Checklist(
        options=[{'label': ' use Rake', 'value': 'use_rake'}],
        value=['use_rake'], id='use_rake'
    ),
    dbc.Checklist(
        options=[{'label': ' use Innervate', 'value': 'use_innervate'}],
        value=[], id='use_innervate'
    ),
    dbc.Checklist(
        options=[{
            'label': ' Mangle / Trauma maintained by bear tank / Arms warrior',
            'value': 'bear_mangle'
        }], value=[], id='bear_mangle'
    ),
    html.Br(),
    html.H5('Trinkets'),
    dbc.Row([
        dbc.Col(dbc.Select(
            id='trinket_1',
            options=[
                {'label': 'Empty', 'value': 'none'},
                {'label': 'Tsunami Talisman', 'value': 'tsunami'},
                {'label': 'Bloodlust Brooch', 'value': 'brooch'},
                {'label': 'Hourglass of the Unraveller', 'value': 'hourglass'},
                {'label': 'Dragonspine Trophy', 'value': 'dst'},
                {'label': 'Mark of the Champion', 'value': 'motc'},
                {'label': "Slayer's Crest", 'value': 'slayers'},
                {'label': 'Drake Fang Talisman', 'value': 'dft'},
                {'label': 'Icon of Unyielding Courage', 'value': 'icon'},
                {'label': 'Abacus of Violent Odds', 'value': 'abacus'},
                {'label': 'Badge of the Swarmguard', 'value': 'swarmguard'},
                {'label': 'Kiss of the Spider', 'value': 'kiss'},
                {'label': 'Badge of Tenacity', 'value': 'tenacity'},
                {
                    'label': 'Living Root of the Wildheart',
                    'value': 'wildheart',
                },
                {
                    'label': 'Ashtongue Talisman of Equilibrium',
                    'value': 'ashtongue',
                },
                {'label': 'Crystalforged Trinket', 'value': 'crystalforged'},
                {'label': 'Madness of the Betrayer', 'value': 'madness'},
                {'label': "Romulo's Poison Vial", 'value': 'vial'},
                {
                    'label': 'Steely Naaru Sliver',
                    'value': 'steely_naaru_sliver'
                },
                {'label': 'Shard of Contempt', 'value': 'shard_of_contempt'},
                {'label': "Berserker's Call", 'value': 'berserkers_call'},
                {'label': "Alchemist's Stone", 'value': 'alch'},
                {
                    'label': "Assassin's Alchemist Stone",
                    'value': 'assassin_alch'
                },
                {'label': 'Blackened Naaru Sliver', 'value': 'bns'},
                {'label': 'Darkmoon Card: Crusade', 'value': 'crusade'},
            ],
            value='shard_of_contempt'
        )),
        dbc.Col(dbc.Select(
            id='trinket_2',
            options=[
                {'label': 'Empty', 'value': 'none'},
                {'label': 'Tsunami Talisman', 'value': 'tsunami'},
                {'label': 'Bloodlust Brooch', 'value': 'brooch'},
                {'label': 'Hourglass of the Unraveller', 'value': 'hourglass'},
                {'label': 'Dragonspine Trophy', 'value': 'dst'},
                {'label': 'Mark of the Champion', 'value': 'motc'},
                {'label': "Slayer's Crest", 'value': 'slayers'},
                {'label': 'Drake Fang Talisman', 'value': 'dft'},
                {'label': 'Icon of Unyielding Courage', 'value': 'icon'},
                {'label': 'Abacus of Violent Odds', 'value': 'abacus'},
                {'label': 'Badge of the Swarmguard', 'value': 'swarmguard'},
                {'label': 'Kiss of the Spider', 'value': 'kiss'},
                {'label': 'Badge of Tenacity', 'value': 'tenacity'},
                {
                    'label': 'Living Root of the Wildheart',
                    'value': 'wildheart',
                },
                {
                    'label': 'Ashtongue Talisman of Equilibrium',
                    'value': 'ashtongue',
                },
                {'label': 'Crystalforged Trinket', 'value': 'crystalforged'},
                {'label': 'Madness of the Betrayer', 'value': 'madness'},
                {'label': "Romulo's Poison Vial", 'value': 'vial'},
                {
                    'label': 'Steely Naaru Sliver',
                    'value': 'steely_naaru_sliver'
                },
                {'label': 'Shard of Contempt', 'value': 'shard_of_contempt'},
                {'label': "Berserker's Call", 'value': 'berserkers_call'},
                {'label': "Alchemist's Stone", 'value': 'alch'},
                {
                    'label': "Assassin's Alchemist Stone",
                    'value': 'assassin_alch'
                },
                {'label': 'Blackened Naaru Sliver', 'value': 'bns'},
                {'label': 'Darkmoon Card: Crusade', 'value': 'crusade'},
            ],
            value='bns'
        )),
    ]),
    html.Div(
        'Make sure not to include passive trinket stats in the sim input.',
        style={
            'marginTop': '2.5%', 'fontSize': 'large', 'fontWeight': 'bold'
        },
    ),
    html.Div([
        dbc.Button(
            "Run", id='run_button', n_clicks=0, size='lg', color='success',
            style={
                'marginBottom': '10%', 'fontSize': 'large', 'marginTop': '10%',
                'display': 'inline-block'
            }
        ),
        html.Div(
            '', id='status',
            style={
                'display': 'inline-block', 'fontWeight': 'bold',
                'marginLeft': '10%', 'fontSize': 'large'
            }
        )
    ]),
    dcc.Interval(id='interval', interval=500),
], width='auto', style={'marginBottom': '2.5%', 'marginLeft': '2.5%'})

input_layout = html.Div(children=[
    html.H1(
        children='WoW Classic WotLK Pre-Patch Feral Cat Simulator',
        style={'textAlign': 'center'}
    ),
    dbc.Row(
        [stat_input, buffs_1, encounter_details, iteration_input],
        style={'marginTop': '2.5%'}
    ),
])

stats_output = dbc.Col(
    [html.H4('Raid Buffed Stats'),
     html.Div([
         html.Div(
             'Swing Timer:',
             style={'width': '50%', 'display': 'inline-block',
                    'fontWeight': 'bold', 'fontSize': 'large'}
         ),
         html.Div(
             '',
             style={'width': '50%', 'display': 'inline-block',
                    'fontSize': 'large'},
             id='buffed_swing_timer'
         )
     ]),
     html.Div([
         html.Div(
             'Attack Power:',
             style={'width': '50%', 'display': 'inline-block',
                    'fontWeight': 'bold', 'fontSize': 'large'}
         ),
         html.Div(
             '',
             style={'width': '50%', 'display': 'inline-block',
                    'fontSize': 'large'},
             id='buffed_attack_power'
         )
     ]),
     html.Div([
         html.Div(
             'Boss Crit Chance:',
             style={'width': '50%', 'display': 'inline-block',
                    'fontWeight': 'bold', 'fontSize': 'large'}
         ),
         html.Div(
             '',
             style={'width': '50%', 'display': 'inline-block',
                    'fontSize': 'large'},
             id='buffed_crit'
         )
     ]),
     html.Div([
         html.Div(
             'Boss Miss Chance:',
             style={'width': '50%', 'display': 'inline-block',
                    'fontWeight': 'bold', 'fontSize': 'large'}
         ),
         html.Div(
             '',
             style={'width': '50%', 'display': 'inline-block',
                    'fontSize': 'large'},
             id='buffed_miss'
         )
     ]),
     html.Div([
         html.Div(
             'Mana:',
             style={'width': '50%', 'display': 'inline-block',
                    'fontWeight': 'bold', 'fontSize': 'large'}
         ),
         html.Div(
             '',
             style={'width': '50%', 'display': 'inline-block',
                    'fontSize': 'large'},
             id='buffed_mana'
         )
     ]),
     html.Div([
         html.Div(
             'Intellect:',
             style={'width': '50%', 'display': 'inline-block',
                    'fontWeight': 'bold', 'fontSize': 'large'}
         ),
         html.Div(
             '',
             style={'width': '50%', 'display': 'inline-block',
                    'fontSize': 'large'},
             id='buffed_int'
         )
     ]),
     html.Div([
         html.Div(
             'Spirit:',
             style={'width': '50%', 'display': 'inline-block',
                    'fontWeight': 'bold', 'fontSize': 'large'}
         ),
         html.Div(
             '',
             style={'width': '50%', 'display': 'inline-block',
                    'fontSize': 'large'},
             id='buffed_spirit'
         )
     ]),
     html.Div([
         html.Div(
             'MP5:',
             style={'width': '50%', 'display': 'inline-block',
                    'fontWeight': 'bold', 'fontSize': 'large'}
         ),
         html.Div(
             '',
             style={'width': '50%', 'display': 'inline-block',
                    'fontSize': 'large'},
             id='buffed_mp5'
         )
     ])],
    width=4, xl=3, style={'marginLeft': '2.5%', 'marginBottom': '2.5%'}
)

sim_output = dbc.Col([
    html.H4('Results'),
    dcc.Loading(children=html.Div([
        html.Div(
            'Average DPS:',
            style={
                'width': '50%', 'display': 'inline-block',
                'fontWeight': 'bold', 'fontSize': 'large'
            }
        ),
        html.Div(
            '',
            style={
                'width': '50%', 'display': 'inline-block', 'fontSize': 'large'
            },
            id='mean_std_dps'
        ),
    ]), id='loading_1', type='default'),
    dcc.Loading(children=html.Div([
        html.Div(
            'Median DPS:',
            style={
                'width': '50%', 'display': 'inline-block',
                'fontWeight': 'bold', 'fontSize': 'large'
            }
        ),
        html.Div(
            '',
            style={
                'width': '50%', 'display': 'inline-block', 'fontSize': 'large'
            },
            id='median_dps'
        ),
    ]), id='loading_2', type='default'),
    dcc.Loading(children=html.Div([
        html.Div(
            'Time to oom:',
            style={
                'width': '50%', 'display': 'inline-block',
                'fontWeight': 'bold', 'fontSize': 'large'
            }
        ),
        html.Div(
            '',
            style={
                'width': '50%', 'display': 'inline-block', 'fontSize': 'large'
            },
            id='time_to_oom'
        ),
    ]), id='loading_oom_time', type='default'),
    html.Br(),
    html.H5('DPS Breakdown'),
    dcc.Loading(children=dbc.Table([
        html.Thead(html.Tr([
            html.Th('Ability'), html.Th('Number of Casts'), html.Th('CPM'),
            html.Th('Damage per Cast'), html.Th('DPS Contribution')
        ])),
        html.Tbody(id='dps_breakdown_table')
    ]), id='loading_3', type='default'),
    html.Br(),
    html.H5('Aura Statistics'),
    dcc.Loading(children=dbc.Table([
        html.Thead(html.Tr([
            html.Th('Aura Name'), html.Th('Number of Procs'),
            html.Th('Average Uptime'),
        ])),
        html.Tbody(id='aura_breakdown_table')
    ]), id='loading_auras', type='default'),
    html.Br(),
    html.Br()
], style={'marginLeft': '2.5%', 'marginBottom': '2.5%'}, width=4, xl=3)

weights_section = dbc.Col([
    html.H4('Stat Weights'),
    html.Div([
        dbc.Row(
            [
                dbc.Col(dbc.Button(
                    'Calculate Weights', id='weight_button', n_clicks=0,
                    color='info'
                ), width='auto'),
                dbc.Col(
                    [
                        dbc.FormGroup(
                            [
                                dbc.Checkbox(
                                    id='calc_mana_weights',
                                    className='form-check-input', checked=False
                                ),
                                dbc.Label(
                                    'Include mana weights',
                                    html_for='calc_mana_weights',
                                    className='form-check-label'
                                )
                            ],
                            check=True
                        ),
                        dbc.FormGroup(
                            [
                                dbc.Checkbox(
                                    id='epic_gems',
                                    className='form-check-input', checked=True
                                ),
                                dbc.Label(
                                    'Assume Epic gems',
                                    html_for='epic_gems',
                                    className='form-check-label'
                                )
                            ],
                            check=True
                        ),
                    ],
                    width='auto'
                )
            ]
        ),
        html.Div(
            'Calculation will take several minutes.',
            style={'fontWeight': 'bold'},
        ),
        dcc.Loading(
            children=[
                html.P(
                    children=[
                        html.Strong(
                            'Error: ', style={'fontSize': 'large'},
                            id='error_str'
                        ),
                        html.Span(
                            'Stat weight calculation requires the simulation '
                            'to be run with at least 20,000 replicates.',
                            style={'fontSize': 'large'}, id='error_msg'
                        )
                    ],
                    style={'marginTop': '4%'},
                ),
                dbc.Table([
                    html.Thead(html.Tr([
                        html.Th('Stat Increment'), html.Th('DPS Added'),
                        html.Th('Normalized Weight')
                    ])),
                    html.Tbody(id='stat_weight_table'),
                ]),
                html.Div(
                    html.A(
                        'Seventy Upgrades Import Link',
                        href='https://seventyupgrades.com', target='_blank'
                    ),
                    id='import_link'
                )
            ],
            id='loading_4', type='default'
        ),
    ]),
], style={'marginLeft': '5%', 'marginBottom': '2.5%'}, width=4, xl=3)

sim_section = dbc.Row(
    [stats_output, sim_output, weights_section]
)

graph_section = html.Div([
    dbc.Row(
        [
            dbc.Col(
                dbc.Button(
                    "Generate Example", id='graph_button', n_clicks=0,
                    color='info',
                    style={'marginLeft': '2.5%', 'fontSize': 'large'}
                ),
                width='auto'
            ),
            dbc.Col(
                dbc.FormGroup(
                    [
                        dbc.Checkbox(
                            id='show_whites', className='form-check-input'
                        ),
                        dbc.Label(
                            'Show white damage', html_for='show_whites',
                            className='form-check-label'
                        )
                    ],
                    check=True
                ),
                width='auto'
            )
        ]
    ),
    html.H4(
        'Example of energy flow in a fight', style={'textAlign': 'center'}
    ),
    dcc.Graph(id='energy_flow'),
    html.Br(),
    dbc.Col(
        [
            html.H5('Combat Log'),
            dbc.Table([
                html.Thead(html.Tr([
                    html.Th('Time'), html.Th('Event'), html.Th('Outcome'),
                    html.Th('Energy'), html.Th('Combo Points'), html.Th('Mana')
                ])),
                html.Tbody(id='combat_log')
            ])
        ],
        width=5, xl=4, style={'marginLeft': '2.5%'}
    )
])

app.layout = html.Div([
    input_layout, sim_section, graph_section
])


# Helper functions used in master callback
def process_trinkets(
        trinket_1, trinket_2, player, ap_mod, stat_mod, haste_multiplier,
        cd_delay
):
    proc_trinkets = []
    all_trinkets = []

    for trinket in [trinket_1, trinket_2]:
        if trinket == 'none':
            continue

        trinket_params = copy.deepcopy(trinkets.trinket_library[trinket])

        for stat, increment in trinket_params['passive_stats'].items():
            if stat == 'intellect':
                increment *= 1.2  # hardcode the HotW 20% increase
            if stat in ['strength', 'agility', 'intellect', 'spirit']:
                increment *= stat_mod
            if stat == 'strength':
                increment *= 2
                stat = 'attack_power'
            if stat == 'agility':
                stat = 'attack_power'
                # additionally modify crit here
                setattr(
                    player, 'crit_chance',
                    getattr(player, 'crit_chance') + increment / 40. / 100.
                )
            if stat == 'attack_power':
                increment *= ap_mod
            if stat == 'haste_rating':
                new_haste_rating = increment + ccs.calc_haste_rating(
                    player.swing_timer, multiplier=haste_multiplier
                )
                new_swing_timer = ccs.calc_swing_timer(
                    new_haste_rating, multiplier=haste_multiplier
                )
                player.swing_timer = new_swing_timer
                continue

            setattr(player, stat, getattr(player, stat) + increment)

        if trinket_params['type'] == 'passive':
            continue

        active_stats = trinket_params['active_stats']

        if active_stats['stat_name'] == 'attack_power':
            active_stats['stat_increment'] *= ap_mod
        if active_stats['stat_name'] == 'Agility':
            active_stats['stat_name'] = ['attack_power', 'crit_chance']
            agi_increment = active_stats['stat_increment']
            active_stats['stat_increment'] = np.array([
                stat_mod * agi_increment * ap_mod,
                stat_mod * agi_increment/40./100.
            ])
        if active_stats['stat_name'] == 'Strength':
            active_stats['stat_name'] = 'attack_power'
            active_stats['stat_increment'] *= 2 * stat_mod * ap_mod

        if trinket_params['type'] == 'activated':
            # If this is the second trinket slot and the first trinket was also
            # activated, then we need to enforce an activation delay due to the
            # shared cooldown. For now we will assume that the shared cooldown
            # is always equal to the duration of the first trinket's proc.
            if all_trinkets and (not proc_trinkets):
                delay = cd_delay + all_trinkets[-1].proc_duration
            else:
                delay = cd_delay

            all_trinkets.append(
                trinkets.ActivatedTrinket(delay=delay, **active_stats)
            )
        else:
            proc_type = active_stats.pop('proc_type')

            if proc_type == 'chance_on_hit':
                proc_chance = active_stats.pop('proc_rate')
                active_stats['chance_on_hit'] = proc_chance
                active_stats['chance_on_crit'] = proc_chance
            elif proc_type == 'chance_on_crit':
                active_stats['chance_on_hit'] = 0.0
                active_stats['chance_on_crit'] = active_stats.pop('proc_rate')
            elif proc_type == 'ppm':
                ppm = active_stats.pop('proc_rate')
                active_stats['chance_on_hit'] = ppm/60.
                active_stats['yellow_chance_on_hit'] = (
                    ppm/60. * player.weapon_speed
                )

            if trinket == 'vial':
                trinket_obj = trinkets.PoisonVial(
                    active_stats['chance_on_hit'],
                    active_stats['yellow_chance_on_hit']
                )
            elif trinket_params['type'] == 'refreshing_proc':
                trinket_obj = trinkets.RefreshingProcTrinket(**active_stats)
            elif trinket_params['type'] == 'stacking_proc':
                trinket_obj = trinkets.StackingProcTrinket(**active_stats)
            else:
                trinket_obj = trinkets.ProcTrinket(**active_stats)

            all_trinkets.append(trinket_obj)
            proc_trinkets.append(all_trinkets[-1])

    player.proc_trinkets = proc_trinkets
    return all_trinkets


def create_player(
        buffed_attack_power, buffed_hit, buffed_crit, buffed_weapon_damage,
        haste_rating, expertise_rating, armor_pen_rating, buffed_mana_pool,
        buffed_int, buffed_spirit, buffed_mp5, weapon_speed, unleashed_rage,
        kings, raven_idol, other_buffs, stat_debuffs, cooldowns, bonuses,
        binary_talents, naturalist, feral_aggression, savage_fury,
        natural_shapeshifter, intensity, potion
):
    """Takes in raid buffed player stats from Eighty Upgrades, modifies them
    based on boss debuffs and miscellaneous buffs not captured by Eighty
    Upgrades, and instantiates a Player object with those stats."""

    # Swing timer calculation is independent of other buffs. First we add up
    # the haste rating from all the specified haste buffs
    buffed_haste_rating = haste_rating
    haste_multiplier = (
        (1 + 0.2 * ('major_haste' in other_buffs))
        * (1 + 0.03 * ('minor_haste' in other_buffs))
    )
    buffed_swing_timer = ccs.calc_swing_timer(
        buffed_haste_rating, multiplier=haste_multiplier
    )

    # Augment secondary stats as needed
    ap_mod = 1.1 * (1 + 0.1 * unleashed_rage)
    debuff_ap = 0
    encounter_crit = (
        buffed_crit + 3 * ('jotc' in stat_debuffs)
        + (28 * ('be_chain' in other_buffs) + 40 * bool(raven_idol)) / 22.1
    )
    encounter_hit = buffed_hit
    encounter_mp5 = buffed_mp5

    # Calculate bonus damage parameters
    encounter_weapon_damage = buffed_weapon_damage
    damage_multiplier = (
        (1 + 0.02 * int(naturalist))
        * (1 + 0.03 * ('sanc_aura' in other_buffs))
    )
    shred_bonus = 88 * ('everbloom' in bonuses) + 75 * ('t5_bonus' in bonuses)

    # Create and return a corresponding Player object
    player = ccs.Player(
        attack_power=buffed_attack_power, hit_chance=encounter_hit / 100,
        expertise_rating=expertise_rating, crit_chance=encounter_crit / 100,
        swing_timer=buffed_swing_timer, mana=buffed_mana_pool,
        intellect=buffed_int, spirit=buffed_spirit, mp5=encounter_mp5,
        omen='omen' in binary_talents,
        primal_gore='primal_gore' in binary_talents,
        feral_aggression=int(feral_aggression), savage_fury=int(savage_fury),
        natural_shapeshifter=int(natural_shapeshifter),
        intensity=int(intensity), weapon_speed=weapon_speed,
        bonus_damage=encounter_weapon_damage, multiplier=damage_multiplier,
        jow='jow' in stat_debuffs, armor_pen_rating=armor_pen_rating,
        t4_bonus='t4_bonus' in bonuses, t6_2p='t6_2p' in bonuses,
        t6_4p='t6_4p' in bonuses, wolfshead='wolfshead' in bonuses,
        meta='meta' in bonuses, rune='rune' in cooldowns,
        pot=potion in ['super', 'fel'], cheap_pot=(potion == 'super'),
        shred_bonus=shred_bonus, debuff_ap=debuff_ap
    )
    return player, ap_mod, (1 + 0.1 * kings) * 1.06 * 1.02, haste_multiplier


def apply_buffs(
        unbuffed_ap, unbuffed_strength, unbuffed_agi, unbuffed_hit,
        unbuffed_crit, unbuffed_mana, unbuffed_int, unbuffed_spirit,
        unbuffed_mp5, weapon_damage, raid_buffs, consumables
):
    """Takes in unbuffed player stats, and turns them into buffed stats based
    on specified consumables and raid buffs. This function should only be
    called if the "Buffs" option is not checked in the exported file from
    Eighty Upgrades, or else the buffs will be double counted!"""

    # Determine "raw" AP, crit, and mana not from Str/Agi/Int
    raw_ap_unbuffed = unbuffed_ap / 1.1 - 2 * unbuffed_strength - unbuffed_agi
    raw_crit_unbuffed = unbuffed_crit - unbuffed_agi / 40
    raw_mana_unbuffed = unbuffed_mana - 15 * unbuffed_int

    # Augment all base stats based on specified buffs
    stat_multiplier = 1 + 0.1 * ('kings' in raid_buffs)
    added_stats = 19.6 * ('motw' in raid_buffs)

    buffed_strength = stat_multiplier * (unbuffed_strength + 1.06 * 1.02 * (
        added_stats + 86 * ('str_totem' in raid_buffs)
    ))
    buffed_agi = stat_multiplier * (unbuffed_agi + 1.06 * 1.02 * (
        added_stats + 86 * ('str_totem' in raid_buffs)
        + 30 * ('agi_elixir' in consumables) + 20 * ('food' in consumables)
    ))
    buffed_int = stat_multiplier * (unbuffed_int + 1.2 * 1.06 * 1.02 * (
        added_stats + 40 * ('ai' in raid_buffs)
        + 30 * ('draenic' in consumables)
    ))
    buffed_spirit = stat_multiplier * (unbuffed_spirit + 1.06 * 1.02 * (
        added_stats + 50 * ('spirit' in raid_buffs)
        + 20 * ('food' in consumables) + 30 * ('draenic' in consumables)
    ))

    # Now augment secondary stats
    ap_mod = 1.1 * (1 + 0.1 * ('unleashed_rage' in raid_buffs))
    buffed_attack_power = ap_mod * (
        raw_ap_unbuffed + 2 * buffed_strength + buffed_agi
        + 306 * 1.25 * ('might' in raid_buffs)
    )
    added_crit_rating = (
        12 * ('agi_elixir' in consumables)
        + 14 * ('weightstone' in consumables)
    )
    buffed_crit = (
        raw_crit_unbuffed + buffed_agi / 40 + added_crit_rating / 22.1
    )
    buffed_hit = (
        unbuffed_hit + 1 * ('heroic_presence' in raid_buffs)
    )
    buffed_mana_pool = raw_mana_unbuffed + buffed_int * 15
    buffed_mp5 = unbuffed_mp5 + 49 * ('wisdom' in raid_buffs)
    buffed_weapon_damage = (
        12 * ('weightstone' in consumables) + weapon_damage
    )

    return {
        'strength': buffed_strength,
        'agility': buffed_agi,
        'intellect': buffed_int,
        'spirit': buffed_spirit,
        'attackPower': buffed_attack_power,
        'crit': buffed_crit,
        'hit': buffed_hit,
        'weaponDamage': buffed_weapon_damage,
        'mana': buffed_mana_pool,
        'mp5': buffed_mp5
    }


def run_sim(sim, num_replicates):
    # Run the sim for the specified number of replicates
    dps_vals, dmg_breakdown, aura_stats, oom_times = sim.run_replicates(
        num_replicates, detailed_output=True
    )

    # Consolidate DPS statistics
    avg_dps = np.mean(dps_vals)
    mean_dps_str = '%.1f +/- %.1f' % (avg_dps, np.std(dps_vals))
    median_dps_str = '%.1f' % np.median(dps_vals)

    # Consolidate mana statistics
    avg_oom_time = np.mean(oom_times)

    if avg_oom_time > sim.fight_length - 1:
        oom_time_str = 'none'
    else:
        oom_time_str = (
            '%d +/- %d seconds' % (avg_oom_time, np.std(oom_times))
        )

    # Create DPS breakdown table
    dps_table = []

    for ability in dmg_breakdown:
        if ability in ['Claw']:
            continue

        ability_dps = dmg_breakdown[ability]['damage'] / sim.fight_length
        ability_cpm = dmg_breakdown[ability]['casts'] / sim.fight_length * 60.
        ability_dpct = ability_dps * 60. / ability_cpm if ability_cpm else 0.
        dps_table.append(html.Tr([
            html.Td(ability),
            html.Td('%.3f' % dmg_breakdown[ability]['casts']),
            html.Td('%.1f' % ability_cpm),
            html.Td('%.0f' % ability_dpct),
            html.Td('%.1f%%' % (ability_dps / avg_dps * 100))
        ]))

    # Create Aura uptime table
    aura_table = []

    for row in aura_stats:
        aura_table.append(html.Tr([
            html.Td(row[0]),
            html.Td('%.3f' % row[1]),
            html.Td('%.1f%%' % (row[2] * 100))
        ]))

    return (
        avg_dps,
        (mean_dps_str, median_dps_str, oom_time_str, dps_table, aura_table),
    )


def append_mana_weights(
        weights_table, sim, num_replicates, time_to_oom, avg_dps, dps_per_AP,
        stat_multiplier
):
    # Just set all mana weights to 0 if we didn't even go oom
    if time_to_oom == 'none':
        weights_table.append(html.Tr([
            html.Td('mana stats'), html.Td('0.0'), html.Td('0.0'),
        ]))
        return

    # Calculate DPS increases and weights
    dps_deltas, stat_weights = sim.calc_mana_weights(
        num_replicates, avg_dps, dps_per_AP
    )

    # Parse results
    for stat in dps_deltas:
        multiplier = 1.0 if stat in ['1 mana', '1 mp5'] else stat_multiplier
        weights_table.append(html.Tr([
            html.Td(stat),
            html.Td('%.3f' % (dps_deltas[stat] * multiplier)),
            html.Td('%.3f' % (stat_weights[stat] * multiplier)),
        ]))


def calc_weights(
        sim, num_replicates, avg_dps, calc_mana_weights, time_to_oom,
        kings, unleashed_rage, epic_gems
):
    # Check that sufficient iterations are used for convergence.
    if num_replicates < 20000:
        error_msg = (
            'Stat weight calculation requires the simulation to be run with at'
            ' least 20,000 replicates.'
        )
        return 'Error: ', error_msg, [], ''

    # Do fresh weights calculation
    weights_table = []

    # Calculate DPS increases and weights
    dps_deltas, stat_weights = sim.calc_stat_weights(
        num_replicates, base_dps=avg_dps, unleashed_rage=unleashed_rage
    )

    # Parse results
    for stat in dps_deltas:
        if stat == '1 AP':
            weight = 1.0
            dps_per_AP = dps_deltas[stat]
        else:
            weight = stat_weights[stat]

        weights_table.append(html.Tr([
            html.Td(stat),
            html.Td('%.2f' % dps_deltas[stat]),
            html.Td('%.2f' % weight),
        ]))

    # Generate 70upgrades import link for raw stats
    stat_multiplier = (1 + 0.1 * kings) * 1.03
    url = ccs.gen_import_link(
        stat_weights, multiplier=stat_multiplier, epic_gems=epic_gems
    )
    link = html.A('Seventy Upgrades Import Link', href=url, target='_blank')

    # Only calculate mana stats if requested
    if calc_mana_weights:
        append_mana_weights(
            weights_table, sim, num_replicates, time_to_oom, avg_dps,
            dps_per_AP, stat_multiplier
        )

    return 'Stat Breakdown', '', weights_table, link


def plot_new_trajectory(sim, show_whites):
    t_vals, _, energy_vals, cp_vals, _, _, log = sim.run(log=True)
    t_fine = np.linspace(0, sim.fight_length, 10000)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=t_fine, y=ccs.piecewise_eval(t_fine, t_vals, energy_vals),
        line=dict(color="#d62728")
    ))
    fig.add_trace(go.Scatter(
        x=t_fine, y=ccs.piecewise_eval(t_fine, t_vals, cp_vals),
        line=dict(color="#9467bd", dash='dash'), yaxis='y2'
    ))
    fig.update_layout(
        xaxis=dict(title='Time (seconds)'),
        yaxis=dict(
            title='Energy', titlefont=dict(color='#d62728'),
            tickfont=dict(color='#d62728')
        ),
        yaxis2=dict(
            title='Combo points', titlefont=dict(color='#9467bd'),
            tickfont=dict(color='#9467bd'), anchor='x', overlaying='y',
            side='right'
        ),
        showlegend=False,
    )

    # Create combat log table
    log_table = []

    if not show_whites:
        parsed_log = [row for row in log if row[1] != 'melee']
    else:
        parsed_log = log

    for row in parsed_log:
        log_table.append(html.Tr([
            html.Td(entry) for entry in row
        ]))

    return fig, log_table


# Master callback function
@app.callback(
    Output('upload_status', 'children'),
    Output('upload_status', 'style'),
    Output('buff_section', 'is_open'),
    Output('buffed_swing_timer', 'children'),
    Output('buffed_attack_power', 'children'),
    Output('buffed_crit', 'children'),
    Output('buffed_miss', 'children'),
    Output('buffed_mana', 'children'),
    Output('buffed_int', 'children'),
    Output('buffed_spirit', 'children'),
    Output('buffed_mp5', 'children'),
    Output('mean_std_dps', 'children'),
    Output('median_dps', 'children'),
    Output('time_to_oom', 'children'),
    Output('dps_breakdown_table', 'children'),
    Output('aura_breakdown_table', 'children'),
    Output('error_str', 'children'),
    Output('error_msg', 'children'),
    Output('stat_weight_table', 'children'),
    Output('import_link', 'children'),
    Output('energy_flow', 'figure'),
    Output('combat_log', 'children'),
    Input('upload-data', 'contents'),
    Input('consumables', 'value'),
    Input('raid_buffs', 'value'),
    Input('other_buffs', 'value'),
    Input('raven_idol', 'value'),
    Input('stat_debuffs', 'value'),
    Input('trinket_1', 'value'),
    Input('trinket_2', 'value'),
    Input('run_button', 'n_clicks'),
    Input('weight_button', 'n_clicks'),
    Input('graph_button', 'n_clicks'),
    State('potion', 'value'),
    State('bonuses', 'value'),
    State('binary_talents', 'value'),
    State('feral_aggression', 'value'),
    State('savage_fury', 'value'),
    State('naturalist', 'value'),
    State('natural_shapeshifter', 'value'),
    State('intensity', 'value'),
    State('fight_length', 'value'),
    State('boss_armor', 'value'),
    State('boss_debuffs', 'value'),
    State('cooldowns', 'value'),
    State('rip_cp', 'value'),
    State('bite_cp', 'value'),
    State('cd_delay', 'value'),
    State('use_rake', 'value'),
    State('use_innervate', 'value'),
    State('use_biteweave', 'value'),
    State('bite_time', 'value'),
    State('bear_mangle', 'value'),
    State('num_replicates', 'value'),
    State('latency', 'value'),
    State('calc_mana_weights', 'checked'),
    State('epic_gems', 'checked'),
    State('show_whites', 'checked'))
def compute(
        json_file, consumables, raid_buffs, other_buffs, raven_idol,
        stat_debuffs, trinket_1, trinket_2, run_clicks, weight_clicks,
        graph_clicks, potion, bonuses, binary_talents, feral_aggression,
        savage_fury, naturalist, natural_shapeshifter, intensity, fight_length,
        boss_armor, boss_debuffs, cooldowns, rip_cp, bite_cp, cd_delay,
        use_rake, use_innervate, use_biteweave, bite_time, bear_mangle,
        num_replicates, latency, calc_mana_weights, epic_gems, show_whites
):
    ctx = dash.callback_context

    # Parse input stats JSON
    buffs_present = False
    use_default_inputs = True

    if json_file is None:
        upload_output = (
            'No file uploaded, using default input stats instead.',
            {'color': '#E59F3A', 'width': 300}, True
        )
    else:
        try:
            content_type, content_string = json_file.split(',')
            decoded = base64.b64decode(content_string)
            input_json = json.load(io.StringIO(decoded.decode('utf-8')))
            buffs_present = input_json['exportOptions']['buffs']
            catform_checked = (
                ('form' in input_json['exportOptions'])
                and (input_json['exportOptions']['form'] == 'cat')
            )

            if not catform_checked:
                upload_output = (
                    'Error processing input file! "Cat Form" was not checked '
                    'in the export pop-up window. Using default input stats '
                    'instead.',
                    {'color': '#D35845', 'width': 300}, True
                )
            elif buffs_present:
                pot_present = False

                for entry in input_json['consumables']:
                    if 'Potion' in entry['name']:
                        pot_present = True

                if pot_present:
                    upload_output = (
                        'Error processing input file! Potions should not be '
                        'checked in the Seventy Upgrades buff tab, as they are'
                        ' temporary rather than permanent stat buffs. Using'
                        ' default input stats instead.',
                        {'color': '#D35845', 'width': 300}, True
                    )
                else:
                    upload_output = (
                        'Upload successful. Buffs detected in Seventy Upgrades'
                        ' export, so the "Consumables" and "Raid Buffs" '
                        'sections in the sim input will be ignored.',
                        {'color': '#5AB88F', 'width': 300}, False
                    )
                    use_default_inputs = False
            else:
                upload_output = (
                    'Upload successful. No buffs detected in Seventy Upgrades '
                    'export, so use the  "Consumables" and "Raid Buffs" '
                    'sections in the sim input for buff entry.',
                    {'color': '#5AB88F', 'width': 300}, True
                )
                use_default_inputs = False
        except Exception:
            upload_output = (
                'Error processing input file! Using default input stats '
                'instead.',
                {'color': '#D35845', 'width': 300}, True
            )

    if use_default_inputs:
        input_stats = copy.copy(default_input_stats)
        buffs_present = False
    else:
        input_stats = input_json['stats']

    # If buffs are not specified in the input file, then interpret the input
    # stats as unbuffed and calculate the buffed stats ourselves.
    if not buffs_present:
        input_stats.update(apply_buffs(
            input_stats['attackPower'], input_stats['strength'],
            input_stats['agility'], input_stats['hit'], input_stats['crit'],
            input_stats['mana'], input_stats['intellect'],
            input_stats['spirit'], input_stats.get('mp5', 0),
            input_stats.get('weaponDamage', 0), raid_buffs, consumables,
        ))

    # Determine whether Unleashed Rage and/or Blessing of Kings are present, as
    # these impact stat weights and buff values.
    if buffs_present:
        unleashed_rage = False
        kings = False

        for buff in input_json['buffs']:
            if buff['name'] == 'Blessing of Kings':
                kings = True
            if buff['name'] == 'Unleashed Rage':
                unleashed_rage = True
    else:
        unleashed_rage = 'unleashed_rage' in raid_buffs
        kings = 'kings' in raid_buffs

    # Create Player object based on raid buffed stat inputs and talents
    player, ap_mod, stat_mod, haste_multiplier = create_player(
        input_stats['attackPower'], input_stats['hit'], input_stats['crit'],
        input_stats.get('weaponDamage', 0), input_stats.get('hasteRating', 0),
        input_stats.get('expertiseRating', 0),
        input_stats.get('armorPenRating', 0),input_stats['mana'],
        input_stats['intellect'], input_stats['spirit'],
        input_stats.get('mp5', 0), float(input_stats['mainHandSpeed']),
        unleashed_rage, kings, raven_idol, other_buffs, stat_debuffs,
        cooldowns, bonuses, binary_talents, naturalist, feral_aggression,
        savage_fury, natural_shapeshifter, intensity, potion
    )

    # Process trinkets
    trinket_list = process_trinkets(
        trinket_1, trinket_2, player, ap_mod, stat_mod, haste_multiplier,
        cd_delay
    )

    # Default output is just the buffed player stats with no further calcs
    stats_output = (
        '%.3f seconds' % player.swing_timer,
        '%d' % player.attack_power,
        '%.2f %%' % (player.crit_chance * 100),
        '%.2f %%' % (player.miss_chance * 100),
        '%d' % player.mana_pool, '%d' % player.intellect,
        '%d' % player.spirit, '%d' % player.mp5
    )

    # Create Simulation object based on specified parameters
    bite = bool(use_biteweave)
    rip_combos = int(rip_cp)

    if 'lust' in cooldowns:
        trinket_list.append(trinkets.Bloodlust(delay=cd_delay))
    if 'drums' in cooldowns:
        trinket_list.append(trinkets.ActivatedTrinket(
            'haste_rating', 80, 'Drums of Battle', 30, 120, delay=cd_delay
        ))

    if 'exalted_ring' in bonuses:
        ring_ppm = 1.0
        ring = trinkets.ProcTrinket(
            chance_on_hit=ring_ppm / 60.,
            yellow_chance_on_hit=ring_ppm / 60. * player.weapon_speed,
            stat_name='attack_power', stat_increment=160 * ap_mod,
            proc_duration=10, cooldown=60,
            proc_name='Band of the Eternal Champion',
        )
        trinket_list.append(ring)
        player.proc_trinkets.append(ring)
    if 'idol_of_terror' in bonuses:
        idol = trinkets.ProcTrinket(
            chance_on_hit=0.85, stat_name=['attack_power', 'crit_chance'],
            stat_increment=np.array([
                65. * stat_mod * ap_mod,
                65. * stat_mod / 40. / 100.,
            ]),
            proc_duration=10, cooldown=10, proc_name='Primal Instinct',
            mangle_only=True
        )
        trinket_list.append(idol)
        player.proc_trinkets.append(idol)
    if 'stag_idol' in bonuses:
        idol = trinkets.RefreshingProcTrinket(
            chance_on_hit=1.0, stat_name='attack_power',
            stat_increment=94 * ap_mod, proc_duration=20, cooldown=0,
            proc_name='Idol of the White Stag', mangle_only=True
        )
        trinket_list.append(idol)
        player.proc_trinkets.append(idol)
    if 'mongoose' in bonuses:
        mongoose_ppm = 0.73
        mongoose_enchant = trinkets.RefreshingProcTrinket(
            stat_name=['attack_power', 'crit_chance', 'haste_rating'],
            stat_increment=np.array([
                120. * stat_mod * ap_mod,
                120. * stat_mod / 40. / 100.,
                30
            ]),
            proc_name='Lightning Speed', chance_on_hit=mongoose_ppm / 60.,
            yellow_chance_on_hit=mongoose_ppm / 60. * player.weapon_speed,
            proc_duration=15, cooldown=0
        )
        trinket_list.append(mongoose_enchant)
        player.proc_trinkets.append(mongoose_enchant)

    if potion == 'haste':
        trinket_list.append(trinkets.HastePotion(delay=cd_delay))

    sim = ccs.Simulation(
        player, fight_length + 1e-9, 0.001 * latency, boss_armor=boss_armor,
        min_combos_for_rip=rip_combos, min_combos_for_bite=int(bite_cp),
        use_innervate=bool(use_innervate), use_rake=bool(use_rake),
        use_bite=bite, bite_time=bite_time, bear_mangle=bool(bear_mangle),
        use_berserk='berserk' in binary_talents, trinkets=trinket_list,
        haste_multiplier=haste_multiplier
    )
    sim.set_active_debuffs(boss_debuffs)
    player.calc_damage_params(**sim.params)

    # If either "Run" or "Stat Weights" button was pressed, then perform a
    # sim run for the specified number of replicates.
    if (ctx.triggered and
            (ctx.triggered[0]['prop_id'] in
             ['run_button.n_clicks', 'weight_button.n_clicks'])):
        avg_dps, dps_output = run_sim(sim, num_replicates)
    else:
        dps_output = ('', '', '', [], [])

    # If "Stat Weights" button was pressed, then calculate weights.
    if (ctx.triggered and
            (ctx.triggered[0]['prop_id'] == 'weight_button.n_clicks')):
        weights_output = calc_weights(
            sim, num_replicates, avg_dps, calc_mana_weights, dps_output[2],
            kings, unleashed_rage, epic_gems
        )
    else:
        weights_output = ('Stat Breakdown', '', [], '')

    # If "Generate Example" button was pressed, do it.
    if (ctx.triggered and
            (ctx.triggered[0]['prop_id'] == 'graph_button.n_clicks')):
        example_output = plot_new_trajectory(sim, show_whites)
    else:
        example_output = ({}, [])

    return (
        upload_output + stats_output + dps_output + weights_output
        + example_output
    )


if __name__ == '__main__':
    multiprocessing.freeze_support()
    app.run_server(
        host='0.0.0.0', port=8080, debug=True
    )
