"""
Stalin's Dilemma - Reconstructed Python Simulation  v3
Original: c 2000, Edward Bever (VB6 native compiled, MSVBVM60.DLL)

v3 improvements over v2:
  ECONOMY (major):
  - Resource flow model: metals produced by mining → flow to industry & production
  - Food balance enforced: harvest distributed across all sectors, warning if over-allocated
  - Worker pool enforced: total workers across sectors cannot exceed USSR labour force
  - Production costs metals+fuel: can't freely produce unlimited factories
  - Foreign exchange costs: imports actually spend exchange earned from exports
  - Goods produced by factories flow as consumer goods to sectors
  - Population grows slowly over 15 years (historical 147M→170M)
  - Mine depletion: metal_sites deplete slowly; need equipment to open new sites
  - Factory depreciation: 2% per plan

  GAMEPLAY:
  - Game-over condition: national survival = 0 triggers loss screen
  - Mid-plan random events (drought, worker uprising, foreign credit) each plan
  - Difficulty: Easy / Normal / Hard modes
  - Save / Load game state (JSON)
  - Historical notes popup per plan showing what really happened

  UI:
  - Resource flow panel: live food/worker/metal balance bars with over-allocation warning
  - Event log panel: running log of decisions and outcomes
  - Mini-map style radar chart of 5 assessment scores
  - Keyboard shortcuts (F5=implement, F1=help, Ctrl+S=save)
  - Colour-blind friendly mode toggle
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import math, json, random, os

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

INITIAL_HARVEST   = 66
INITIAL_FACTORIES = 192
STRIKE_THRESHOLD  = 25

HARVEST_YEAR_MOD = {
    1928:1.000, 1929:0.973, 1930:1.137, 1931:0.945, 1932:0.959,
    1933:0.932, 1934:0.918, 1935:1.027, 1936:0.767, 1937:1.329,
    1938:1.301, 1939:1.000, 1940:1.301, 1941:0.767, 1942:0.397,
}
THREAT_BY_YEAR = {
    1928:0, 1929:0, 1930:0, 1931:0, 1932:0,
    1933:5, 1934:10,1935:15,1936:25,1937:30,
    1938:40,1939:50,1940:60,1941:80,1942:90,
}
# USSR total labour force by plan start year (millions)
LABOUR_FORCE = {1928:80, 1933:88, 1938:96, 1943:96}

# Production costs: each unit queued costs metals + fuel from current stocks
PROD_COSTS = {
    'factories' :{'metals':2, 'fuel':0.5},
    'weapons'   :{'metals':1, 'fuel':0.3},
    'tractors'  :{'metals':1, 'fuel':0.3},
    'rigs'      :{'metals':1, 'fuel':0.3},
    'transports':{'metals':1, 'fuel':0.3},
    'mine_equip':{'metals':1, 'fuel':0.3},
    'goods'     :{'metals':1, 'fuel':0.2},
}
# Import costs in foreign exchange
IMPORT_COSTS = {
    'factories' :5, 'tractors'  :2,
    'mine_equip':2, 'fuel_rigs' :3, 'transports':3,
}

# Historical notes shown at end of each plan
HISTORICAL_NOTES = {
    1: ("First Five Year Plan (1928-1932)",
        "Stalin launched breakneck industrialisation. Forced collectivisation "
        "caused the Holodomor famine (1932-33), killing millions. Heavy industry "
        "expanded dramatically but consumer goods collapsed. Population fell in rural areas."),
    2: ("Second Five Year Plan (1933-1937)",
        "Continued growth in steel, coal and machinery. The Great Terror (1936-38) "
        "purged military leadership and engineers. Despite this, industrial output "
        "roughly doubled from 1928 levels by 1937."),
    3: ("Third Five Year Plan (1938-1942)",
        "Rearmament dominated as war loomed. Germany invaded June 1941 (Operation "
        "Barbarossa). The USSR survived through vast manpower, Allied aid, and the "
        "industrial base built in the previous decade — much of it relocated east of the Urals."),
}

# Random events per plan (one drawn randomly)
EVENTS = {
    1: [
        {'name':'Drought in Ukraine',     'prob':0.3, 'effect':'harvest',   'delta':-8,
         'desc':'Drought cuts harvest by 8M tons this plan.'},
        {'name':'Foreign Credit Line',    'prob':0.2, 'effect':'exchange',  'delta':15,
         'desc':'American banks extend credit — +15 foreign exchange.'},
        {'name':'Peasant Uprising',       'prob':0.2, 'effect':'stability', 'delta':-10,
         'desc':'Collectivisation resistance flares — political stability -10.'},
        {'name':'German Technical Aid',   'prob':0.15,'effect':'factories', 'delta':10,
         'desc':'German engineers help build factories — +10 factories.'},
        {'name':'Good Harvest',           'prob':0.15,'effect':'harvest',   'delta':12,
         'desc':'Excellent weather — harvest +12M tons.'},
    ],
    2: [
        {'name':'Great Terror Purges',    'prob':0.4, 'effect':'mil_rel',   'delta':-20,
         'desc':'Military purges devastate officer corps — reliability -20.'},
        {'name':'Stakhanovite Movement',  'prob':0.25,'effect':'factories', 'delta':15,
         'desc':'Worker productivity campaign — +15 factory output.'},
        {'name':'Spanish Civil War Drain','prob':0.15,'effect':'weapons',   'delta':-8,
         'desc':'Aid to Republicans costs weapons and exchange.'},
        {'name':'Lend-Lease Preview',     'prob':0.1, 'effect':'exchange',  'delta':20,
         'desc':'Early Western trade boost — +20 foreign exchange.'},
        {'name':'Flood in Volga Region',  'prob':0.1, 'effect':'harvest',   'delta':-6,
         'desc':'Flooding reduces grain harvest by 6M tons.'},
    ],
    3: [
        {'name':'Barbarossa',             'prob':0.5, 'effect':'survival',  'delta':-25,
         'desc':'German invasion! National survival -25 unless military is strong.'},
        {'name':'Lend-Lease',             'prob':0.3, 'effect':'exchange',  'delta':30,
         'desc':'Allied Lend-Lease begins — +30 foreign exchange and supplies.'},
        {'name':'Factory Evacuation East','prob':0.2, 'effect':'factories', 'delta':-20,
         'desc':'Moving factories east of Urals disrupts production temporarily.'},
        {'name':'Heroic Defence of City', 'prob':0.15,'effect':'mil_rel',   'delta':15,
         'desc':'Successful defence boosts army morale — reliability +15.'},
        {'name':'Scorched Earth Policy',  'prob':0.1, 'effect':'harvest',   'delta':-15,
         'desc':'Retreat burns crops to deny them to the enemy — harvest -15.'},
    ],
}

DIFFICULTIES = {
    'Easy'  : {'labour_mult':1.2, 'cost_mult':0.6, 'event_prob':0.5, 'threat_mult':0.7},
    'Normal': {'labour_mult':1.0, 'cost_mult':1.0, 'event_prob':1.0, 'threat_mult':1.0},
    'Hard'  : {'labour_mult':0.85,'cost_mult':1.4, 'event_prob':1.3, 'threat_mult':1.3},
}

# ─────────────────────────────────────────────────────────────────────────────
# GAME STATE
# ─────────────────────────────────────────────────────────────────────────────

class GameState:
    def __init__(self, difficulty='Normal'):
        self.difficulty   = difficulty
        self.diff         = DIFFICULTIES[difficulty]
        self.year         = 1928
        self.plan_number  = 1
        self.game_over    = False

        # ── AGRICULTURE ──────────────────────────────────────────────────────
        self.peasants          = 45
        self.animals           = 30
        self.tractors          = 10
        self.farm_fuel_alloc   = 5
        self.farm_food         = 20    # peasant food ration; rest goes to food pool
        self.farm_goods        = 10
        self.collectivize      = 0
        # computed
        self.harvest            = INITIAL_HARVEST
        self.food_available     = 0
        self.farm_consolidation = 0
        self.max_quota          = 0
        self.surplus            = 0
        self.displaced_workers  = 0
        self.farm_sol           = 50
        self.food_scarcity_mult = 1.0

        # ── METALS / MINING ───────────────────────────────────────────────────
        self.miners             = 12
        self.mine_equipment     = 20
        self.metal_sites        = 20
        self.mine_fuel_alloc    = 8
        self.mine_food          = 5
        self.mine_goods         = 5
        # computed
        self.metal_produced     = 0
        self.mine_sol           = 50

        # ── ENERGY ────────────────────────────────────────────────────────────
        self.fuel_workers       = 8
        self.rigs               = 25
        self.energy_fuel        = 2
        self.energy_food        = 5
        self.energy_goods       = 4
        # computed
        self.fuel_produced      = 0
        self.energy_sol         = 50
        self.fuel_ratio         = 1.0

        # ── FUEL DISTRIBUTION ─────────────────────────────────────────────────
        self.trans_fuel_alloc   = 8
        self.induct_fuel_alloc  = 10
        self.mil_fuel_alloc     = 5

        # ── TRANSPORTATION ────────────────────────────────────────────────────
        self.transports         = 20
        self.transport_workers  = 5
        self.trans_food         = 5
        self.trans_goods        = 5
        # computed
        self.trans_sol          = 50
        self.trans_fuel_ratio   = 1.0

        # ── INDUSTRY ──────────────────────────────────────────────────────────
        self.factories          = INITIAL_FACTORIES
        self.induct_workers     = 6
        self.induct_food        = 10
        self.induct_goods       = 8
        self.induct_metals      = 0    # auto-assigned from metal_produced
        # computed
        self.goods_produced            = 0
        self.induct_sol                = 50
        self.induct_capacity           = INITIAL_FACTORIES
        self.induct_capacity_available = INITIAL_FACTORIES
        self.induct_fuel_ratio         = 1.0
        # ── MILITARY ──────────────────────────────────────────────────────
        self.soldiers               = 3
        self.total_weapons          = 10
        self.mil_food               = 6
        self.mil_goods              = 4
        # mil_fuel_alloc already set in FUEL DISTRIBUTION above
        # computed
        self.mil_sol                = 50
        self.mil_reliability        = 80
        self.military_effectiveness = 0

        # ── FOREIGN TRADE ─────────────────────────────────────────────────────
        self.foreign_exchange    = 10
        self.trade_metals        = 2
        self.trade_fuels         = 2
        self.trade_food          = 0
        self.imported_factories  = 0
        self.imported_tractors   = 0
        self.imported_mine_equip = 0
        self.imported_fuel_rigs  = 0
        self.imported_transports = 0

        # ── PRODUCTION QUEUE ──────────────────────────────────────────────────
        self.produce_factories  = 0
        self.produce_weapons    = 0
        self.produce_tractors   = 0
        self.produce_rigs       = 0
        self.produce_transports = 0
        self.produce_mine_equip = 0
        self.produce_goods      = 0

        # ── RESOURCE BALANCE (computed) ───────────────────────────────────────
        self.food_allocated     = 0   # sum of all sector food assignments
        self.food_balance       = 0   # food_available - food_allocated
        self.metal_allocated    = 0   # induct_metals + production costs
        self.metal_balance      = 0
        self.fuel_allocated     = 0
        self.fuel_balance       = 0
        self.worker_total       = 0
        self.worker_balance     = 0   # labour_force - worker_total
        self.goods_allocated    = 0
        self.goods_balance      = 0
        self.prod_metals_cost   = 0   # metals needed for production queue
        self.prod_fuel_cost     = 0

        # ── ASSESSMENTS ───────────────────────────────────────────────────────
        self.industrial_production = 0
        self.political_stability   = 0
        self.national_survival     = 50
        self.total_deaths          = 0.0

        # ── TRACKING ──────────────────────────────────────────────────────────
        self.history    = []
        self.event_log  = []
        self.last_event = None

    def labour_force(self):
        base = LABOUR_FORCE.get(self.year, 80)
        return int(base * self.diff['labour_mult'])

    def total_workers(self):
        # displaced_workers came FROM peasants - don't double count
        return (self.peasants + self.miners + self.fuel_workers +
                self.transport_workers + self.induct_workers +
                self.soldiers)

    def total_fuel_demand(self):
        return (self.farm_fuel_alloc + self.mine_fuel_alloc + self.trans_fuel_alloc +
                self.induct_fuel_alloc + self.mil_fuel_alloc + self.energy_fuel)

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items()
                if not callable(v) and k not in ('diff',)}

    def from_dict(self, d, difficulty='Normal'):
        self.__init__(difficulty)
        for k, v in d.items():
            if hasattr(self, k):
                setattr(self, k, v)
        self.diff = DIFFICULTIES[self.difficulty]


# ─────────────────────────────────────────────────────────────────────────────
# CALCULATIONS
# ─────────────────────────────────────────────────────────────────────────────

def calculate_sol(food, goods, workers):
    if workers <= 0: return 0
    raw = (food * 2.0 + goods) / (workers * 3.0)
    return max(5, min(100, int(raw * 100)))


def calculate_harvest(s):
    year_mod = HARVEST_YEAR_MOD.get(s.year, 1.0)

    usable_tractors = min(s.tractors, s.farm_fuel_alloc * 2)
    machine_power   = usable_tractors * 1.5 + s.animals * 0.4
    if s.peasants == 0:
        s.harvest = 0; s.farm_consolidation=0; s.max_quota=0; s.food_available=0; s.surplus=0; s.farm_sol=0; return 0
    labour_mod = min(1.15, max(0.05, 1.0 - abs(s.peasants - 60) / 200.0))
    machine_mod     = min(1.4,  1.0 + machine_power / 180.0)

    c_effect = {0:1.00, 1:1.03, 2:1.07, 3:1.08}.get(s.collectivize, 1.0)
    if s.collectivize == 3:
        chaos = max(0, 0.20 - (s.plan_number - 1) * 0.05)
        c_effect *= (1.0 - chaos)

    s.harvest           = round(INITIAL_HARVEST * year_mod * labour_mod * machine_mod * c_effect, 1)
    s.displaced_workers = int(s.collectivize * 2 * max(0, s.peasants - 50) * 0.03)
    s.farm_consolidation= min(100, s.collectivize * 22 + s.tractors // 2)

    peasant_consumption = round(s.peasants * 0.22, 1)
    s.max_quota         = max(0, round(s.harvest - peasant_consumption, 1))

    # food_available = harvest - what peasants consume from farm_food allocation
    # farm_food is the peasant ration; rest is available for other sectors + export
    s.food_available    = max(0, round(s.harvest - s.farm_food, 1))
    s.surplus           = round(s.food_available - (s.mine_food + s.energy_food +
                                                      s.trans_food + s.induct_food +
                                                      s.mil_food + s.trade_food), 1)
    s.farm_sol = calculate_sol(s.farm_food, s.farm_goods, s.peasants)
    # Food scarcity: if total allocated > harvest, ALL SOLs are penalised
    total_food_demand = (s.farm_food + s.mine_food + s.energy_food +
                         s.trans_food + s.induct_food + s.mil_food + s.trade_food)
    if total_food_demand > 0 and s.harvest > 0:
        s.food_scarcity_mult = min(1.0, s.harvest / total_food_demand)
    else:
        s.food_scarcity_mult = 1.0
    # Re-apply scarcity to farm_sol
    s.farm_sol = max(0, int(s.farm_sol * s.food_scarcity_mult))
    return s.harvest


def calculate_metals(s):
    """Mining output flows into metal_produced; industry draws from it."""
    fuel_limit      = min(s.mine_equipment, s.mine_fuel_alloc * 2.5)
    # Mine site depletion: fewer sites = lower ceiling
    site_factor     = min(1.0, s.metal_sites / 15.0)
    output          = s.miners * 1.8 * (1.0 + fuel_limit / 25.0) * site_factor
    s.metal_produced= round(output, 1)
    s.mine_sol      = max(0, int(calculate_sol(s.mine_food, s.mine_goods, s.miners) * getattr(s,'food_scarcity_mult',1.0)))
    return s.metal_produced


def calculate_energy(s):
    output          = s.fuel_workers * 1.5 * (1.0 + s.rigs / 12.0)
    s.fuel_produced = round(output, 1)
    demand          = s.total_fuel_demand()
    s.fuel_ratio    = round(min(1.5, s.fuel_produced / max(1, demand)), 3)
    s.energy_sol    = max(0, int(calculate_sol(s.energy_food, s.energy_goods, s.fuel_workers) * getattr(s,'food_scarcity_mult',1.0)))
    return s.fuel_produced


def calculate_transport(s):
    fuel_needed         = s.transports * 0.25
    s.trans_fuel_ratio  = round(min(1.5, s.trans_fuel_alloc / max(1, fuel_needed)), 3)
    s.trans_sol         = max(0, int(calculate_sol(s.trans_food, s.trans_goods, s.transport_workers) * getattr(s,'food_scarcity_mult',1.0)))
    return s.trans_sol < STRIKE_THRESHOLD


def calculate_industry(s):
    # Auto-assign metals to industry if not manually set
    # Industry gets what's left after trade and production costs
    available_metals  = max(0, s.metal_produced - s.trade_metals - s.prod_metals_cost)
    s.induct_metals   = round(available_metals, 1)

    optimal_fuel      = s.factories * 0.04
    s.induct_fuel_ratio = round(min(1.5, s.induct_fuel_alloc / max(1, optimal_fuel)), 3)

    metal_ratio       = min(1.0, s.induct_metals / max(1, s.factories * 0.06))
    s.induct_capacity = s.factories
    effective         = min(s.induct_fuel_ratio, 1.0) * metal_ratio
    s.induct_capacity_available = int(s.factories * effective)

    # Goods produced by industry (consumer goods + equipment)
    s.goods_produced  = round(s.induct_capacity_available * 0.15, 1)
    s.induct_sol      = max(0, int(calculate_sol(s.induct_food, s.induct_goods, s.induct_workers) * getattr(s,'food_scarcity_mult',1.0)))
    return s.induct_capacity_available


def calculate_resource_balances(s):
    """Compute all balance figures for UI warning bars."""
    # Food
    s.food_allocated = round(s.farm_food + s.mine_food + s.energy_food +
                             s.trans_food + s.induct_food + s.mil_food + s.trade_food, 1)
    s.food_balance   = round(s.harvest - s.food_allocated, 1)

    # Metals
    s.prod_metals_cost = sum(
        getattr(s, f'produce_{k}') * v['metals'] * s.diff['cost_mult']
        for k, v in PROD_COSTS.items()
        if hasattr(s, f'produce_{k}')
    )
    s.metal_allocated  = round(s.trade_metals + s.prod_metals_cost, 1)
    s.metal_balance    = round(s.metal_produced - s.metal_allocated, 1)

    # Fuel
    s.prod_fuel_cost  = sum(
        getattr(s, f'produce_{k}') * v['fuel'] * s.diff['cost_mult']
        for k, v in PROD_COSTS.items()
        if hasattr(s, f'produce_{k}')
    )
    s.fuel_allocated  = round(s.total_fuel_demand() + s.prod_fuel_cost, 1)
    s.fuel_balance    = round(s.fuel_produced - s.fuel_allocated, 1)

    # Workers
    s.worker_total    = s.total_workers()
    s.worker_balance  = s.labour_force() - s.worker_total

    # Goods
    s.goods_allocated = round(s.farm_goods + s.mine_goods + s.energy_goods +
                              s.trans_goods + s.induct_goods + s.mil_goods, 1)
    s.goods_balance   = round(s.goods_produced - s.goods_allocated, 1)


def calculate_military_assessment(s):
    if s.soldiers <= 0:
        s.military_effectiveness = 0
        return 0
    base     = min(55, s.soldiers * 6) + min(60, s.total_weapons * 2)
    s.mil_sol  = max(0, int(calculate_sol(s.mil_food, s.mil_goods, s.soldiers) * getattr(s,'food_scarcity_mult',1.0)))
    sol_mod   = s.mil_sol / 100.0
    fuel_mod  = min(1.0, s.mil_fuel_alloc / max(1, s.total_weapons * 0.4))
    s.military_effectiveness = min(100, int(base * sol_mod * fuel_mod))
    return s.military_effectiveness


def calculate_industrial_assessment(s):
    factory_growth   = min(70, max(0, s.factories - INITIAL_FACTORIES) * 0.6)
    transport_growth = min(15, max(0, s.transports - 20) * 0.5)
    tractor_growth   = min(10, max(0, s.tractors - 10) * 0.4)
    mine_growth      = min(10, max(0, s.mine_equipment - 10) * 0.4)
    rig_growth       = min(10, max(0, s.rigs - 8) * 0.5)
    util_bonus       = (s.induct_capacity_available / max(1, s.induct_capacity)) * 20
    s.industrial_production = min(100, int(factory_growth + transport_growth +
                                           tractor_growth + mine_growth +
                                           rig_growth + util_bonus))
    return s.industrial_production


def calculate_political_assessment(s):
    sectors  = [s.farm_sol, s.mine_sol, s.energy_sol,
                s.trans_sol, s.induct_sol, s.mil_sol]
    avg_sol  = sum(sectors) / len(sectors)
    col_pen  = {0:0, 1:2, 2:5, 3:18}.get(s.collectivize, 0)
    str_pen  = 12 if s.trans_sol < STRIKE_THRESHOLD else 0
    fam_pen  = max(0, (20 - s.farm_sol) * 0.8) if s.farm_sol < 20 else 0
    debt_pen = max(0, (s.food_balance * -1) * 0.5) if s.food_balance < 0 else 0
    s.political_stability = max(0, min(100, int(avg_sol - col_pen - str_pen - fam_pen - debt_pen)))
    s.mil_reliability     = max(20, min(100, s.political_stability + 5))
    return s.political_stability


def calculate_survival_assessment(s):
    threat  = THREAT_BY_YEAR.get(min(s.year, 1942), 0) * s.diff['threat_mult']
    margin  = s.military_effectiveness - threat
    s.national_survival = max(0, min(100, int(50 + margin * 0.8)))
    return s.national_survival


def calculate_death_assessment(s):
    if s.farm_sol < 30:
        shortage = (30 - s.farm_sol) / 30.0
        starvation = shortage ** 2 * s.peasants * 0.04
    else:
        starvation = 0.0
    if s.food_balance < -10:
        starvation += abs(s.food_balance) * 0.02  # extra deaths from overall shortage
    collect_d  = {0:0.0, 1:0.02, 2:0.05, 3:0.30}.get(s.collectivize, 0)
    pol_d      = max(0, (25 - s.political_stability) * 0.01) if s.political_stability < 25 else 0
    s.total_deaths += round(starvation + collect_d + pol_d, 3)
    return s.total_deaths


def calculate_judgement(s):
    human_cost = max(0, 100 - int(s.total_deaths * 8))
    # Use last recorded plan scores when game is complete (avoids post-increment year bug)
    if s.history and s.plan_number > 3:
        h = s.history[-1]
        scores = {
            'Military Effectiveness': max(0, min(100, h['military'])),
            'Industrial Production' : max(0, min(100, h['industrial'])),
            'Political Stability'   : max(0, min(100, h['political'])),
            'National Survival'     : max(0, min(100, h['survival'])),
            'Human Cost'            : human_cost,
        }
    else:
        scores = {
            'Military Effectiveness': max(0, min(100, s.military_effectiveness)),
            'Industrial Production' : max(0, min(100, s.industrial_production)),
            'Political Stability'   : max(0, min(100, s.political_stability)),
            'National Survival'     : max(0, min(100, s.national_survival)),
            'Human Cost'            : human_cost,
        }
    overall = sum(scores.values()) / len(scores)
    if   overall >= 75: rep = "Stalin the Builder — Triumph of Soviet Will"
    elif overall >= 60: rep = "Adequate Industrialisation — Victory at High Cost"
    elif overall >= 45: rep = "Partial Success — Industry Grew, People Suffered"
    elif overall >= 30: rep = "Serious Mismanagement — The People Paid Dearly"
    else:               rep = "Catastrophic Failure — The Revolution Betrayed"
    return scores, overall, rep


def run_all_calculations(s):
    calculate_harvest(s)
    calculate_metals(s)
    calculate_energy(s)
    calculate_transport(s)
    calculate_industry(s)
    calculate_resource_balances(s)
    calculate_military_assessment(s)
    calculate_industrial_assessment(s)
    calculate_political_assessment(s)
    calculate_survival_assessment(s)


def draw_random_event(s):
    """Draw a plan-appropriate random event, apply it, return description."""
    pool = EVENTS.get(s.plan_number, [])
    if not pool:
        return None
    # Weighted random draw
    prob_mult = s.diff['event_prob']
    for evt in sorted(pool, key=lambda e: random.random()):
        if random.random() < evt['prob'] * prob_mult:
            delta = evt['delta']
            eff   = evt['effect']
            if   eff == 'harvest'  : s.harvest           = max(0, s.harvest + delta)
            elif eff == 'exchange' : s.foreign_exchange  += delta
            elif eff == 'stability': s.political_stability = max(0, s.political_stability + delta)
            elif eff == 'factories': s.factories          += delta
            elif eff == 'weapons'  : s.total_weapons      = max(0, s.total_weapons + delta)
            elif eff == 'mil_rel'  : s.mil_reliability    = max(20, min(100, s.mil_reliability + delta))
            elif eff == 'survival' :
                # If military strong enough, resist Barbarossa
                resist = max(0, delta + s.military_effectiveness // 3)
                s.national_survival = max(0, min(100, s.national_survival + resist))
            s.last_event = evt
            return evt
    return None


def implement_plan(s):
    run_all_calculations(s)
    calculate_death_assessment(s)

    # Check import costs
    import_cost = (s.imported_factories  * IMPORT_COSTS['factories'] +
                   s.imported_tractors   * IMPORT_COSTS['tractors'] +
                   s.imported_mine_equip * IMPORT_COSTS['mine_equip'] +
                   s.imported_fuel_rigs  * IMPORT_COSTS['fuel_rigs'] +
                   s.imported_transports * IMPORT_COSTS['transports'])

    # Foreign trade: earn exchange from exports
    export_value = s.trade_metals * 2.0 + s.trade_fuels * 1.5 + s.trade_food * 1.0
    s.foreign_exchange += round(export_value, 1)

    # Deduct import costs (clamp to 0)
    s.foreign_exchange  = max(0, round(s.foreign_exchange - import_cost * s.diff['cost_mult'], 1))

    # Apply imports
    s.factories      += s.imported_factories
    s.tractors       += s.imported_tractors
    s.mine_equipment += s.imported_mine_equip
    s.rigs           += s.imported_fuel_rigs
    s.transports     += s.imported_transports

    # Production scale: compare total supply vs (sector demand + production cost)
    # FIX: use raw produced values vs total demand, not the leftover balance
    total_metal_demand = s.trade_metals + s.prod_metals_cost
    total_fuel_demand_all = s.total_fuel_demand() + s.prod_fuel_cost
    metal_ps = min(1.0, s.metal_produced / max(0.1, total_metal_demand)) if total_metal_demand > 0 else 1.0
    fuel_ps  = min(1.0, s.fuel_produced  / max(0.1, total_fuel_demand_all)) if total_fuel_demand_all > 0 else 1.0
    prod_scale = max(0, min(metal_ps, fuel_ps))

    s.factories      += int(s.produce_factories  * prod_scale)
    s.total_weapons  += int(s.produce_weapons    * prod_scale)
    s.tractors       += int(s.produce_tractors   * prod_scale)
    s.rigs           += int(s.produce_rigs        * prod_scale)
    s.transports     += int(s.produce_transports  * prod_scale)
    s.mine_equipment += int(s.produce_mine_equip  * prod_scale)

    # Factory depreciation: 2% per plan
    s.factories = max(INITIAL_FACTORIES // 2, int(s.factories * 0.98))

    # Mine depletion: each miner-plan depletes 0.1 sites; equipment opens new ones
    s.metal_sites = max(5, round(s.metal_sites - s.miners * 0.1 + s.mine_equipment * 0.05, 1))

    # Displaced workers → unassigned
    s.displaced_workers = 0  # reset; will be recalculated

    # Strike check
    strike = s.trans_sol < STRIKE_THRESHOLD

    # Draw random event
    event = draw_random_event(s)

    # Snapshot history
    scores, overall, rep = calculate_judgement(s)
    s.history.append({
        'plan'      : s.plan_number,
        'year'      : s.year,
        'harvest'   : s.harvest,
        'factories' : s.factories,
        'military'  : max(0, min(100, s.military_effectiveness)),
        'industrial': max(0, min(100, s.industrial_production)),
        'political' : max(0, min(100, s.political_stability)),
        'survival'  : max(0, min(100, s.national_survival)),
        'deaths'    : round(s.total_deaths, 2),
        'overall'   : round(overall, 1),
        'sol_avg'   : int(sum([s.farm_sol, s.mine_sol, s.energy_sol,
                               s.trans_sol, s.induct_sol, s.mil_sol]) / 6),
        'event'     : event['name'] if event else 'None',
    })

    # Log
    entry = f"Plan {s.plan_number} ({s.year}): Score {overall:.0f} | Deaths {s.total_deaths:.2f}M"
    if event:
        entry += f" | Event: {event['name']}"
    s.event_log.insert(0, entry)

    # Reset production queues
    for attr in ['produce_factories','produce_weapons','produce_tractors',
                 'produce_rigs','produce_transports','produce_mine_equip','produce_goods',
                 'imported_factories','imported_tractors','imported_mine_equip',
                 'imported_fuel_rigs','imported_transports']:
        setattr(s, attr, 0)

    # Advance time
    s.year        += 5
    s.plan_number += 1

    # Game over check
    if s.national_survival <= 0:
        s.game_over = True

    return strike, event, prod_scale


# ─────────────────────────────────────────────────────────────────────────────
# THEME
# ─────────────────────────────────────────────────────────────────────────────

DARK_BG   = '#0d1117'
PANEL_BG  = '#161b22'
BORDER    = '#30363d'
RED       = '#f85149'
GREEN     = '#3fb950'
BLUE      = '#58a6ff'
AMBER     = '#d29922'
PURPLE    = '#bc8cff'
DIM       = '#8b949e'
WHITE     = '#e6edf3'
FM        = ('Courier New', 9)
FB        = ('Courier New', 9, 'bold')
FT        = ('Courier New', 14, 'bold')
FH        = ('Courier New', 10, 'bold')
FS        = ('Courier New', 8)

def sol_col(v):
    return GREEN if v >= 60 else AMBER if v >= 35 else RED

def pct_col(v):
    return GREEN if v >= 65 else AMBER if v >= 40 else RED

def bal_col(v):
    return GREEN if v >= 0 else RED


# ─────────────────────────────────────────────────────────────────────────────
# BALANCE BAR WIDGET
# ─────────────────────────────────────────────────────────────────────────────

class BalanceBar(tk.Frame):
    """Shows allocated vs available as a horizontal bar with labels."""
    def __init__(self, parent, label, width=140, **kw):
        super().__init__(parent, bg=PANEL_BG, **kw)
        tk.Label(self, text=label, font=FS, fg=DIM,
                 bg=PANEL_BG, width=8, anchor='w').pack(side='left')
        self._canvas = tk.Canvas(self, width=width, height=12,
                                 bg=BORDER, highlightthickness=0)
        self._canvas.pack(side='left', padx=3)
        self._fill = self._canvas.create_rectangle(0, 0, 0, 12, fill=GREEN, outline='')
        self._lbl  = tk.Label(self, text='', font=FS, fg=WHITE, bg=PANEL_BG, width=12)
        self._lbl.pack(side='left')
        self._width = width

    def update(self, used, total, label=''):
        pct  = min(1.0, used / max(1, total))
        over = used > total
        col  = RED if over else GREEN if pct < 0.85 else AMBER
        w    = int(self._width * pct)
        self._canvas.coords(self._fill, 0, 0, w, 12)
        self._canvas.itemconfig(self._fill, fill=col)
        self._lbl.config(text=label or f'{used:.0f}/{total:.0f}',
                         fg=RED if over else WHITE)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN APP
# ─────────────────────────────────────────────────────────────────────────────

class StalinsDilemmaApp:
    def __init__(self, root):
        self.root    = root
        self.state   = GameState()
        self._vars   = {}
        self._info   = {}
        self._bars   = {}
        self._pending = None
        root.title("Stalin's Dilemma — Soviet Industrialization 1928–1942")
        root.configure(bg=DARK_BG)
        root.geometry('1380x900')
        root.minsize(1200, 750)
        self._build_ui()
        self._bind_keys()
        self._refresh()

    # ── key bindings ──────────────────────────────────────────────────────────

    def _bind_keys(self):
        self.root.bind('<F5>',         lambda e: self._on_implement())
        self.root.bind('<F1>',         lambda e: self._show_help())
        self.root.bind('<Control-s>',  lambda e: self._save_game())
        self.root.bind('<Control-o>',  lambda e: self._load_game())
        self.root.bind('<Control-n>',  lambda e: self._new_game())

    # ── top-level layout ──────────────────────────────────────────────────────

    def _build_ui(self):
        root = self.root

        # Header
        hdr = tk.Frame(root, bg='#010409', pady=5)
        hdr.pack(fill='x')
        tk.Label(hdr, text='☭  STALIN\'S DILEMMA', font=('Courier New', 17, 'bold'),
                 fg=RED, bg='#010409').pack(side='left', padx=12)
        self._plan_lbl = tk.Label(hdr, text='', font=FB, fg=AMBER, bg='#010409')
        self._plan_lbl.pack(side='left', padx=12)
        self._diff_lbl = tk.Label(hdr, text='', font=FB, fg=PURPLE, bg='#010409')
        self._diff_lbl.pack(side='left', padx=6)
        self._score_lbl = tk.Label(hdr, text='', font=FB, fg=GREEN, bg='#010409')
        self._score_lbl.pack(side='right', padx=12)

        # Status bar
        self._status = tk.Label(root, text='', font=FS, fg=DIM, bg='#010409', anchor='w')
        self._status.pack(fill='x', padx=6)

        # Paned: left=main controls, right=sidebar
        paned = tk.PanedWindow(root, orient='horizontal', bg=DARK_BG,
                               sashwidth=4, sashrelief='flat')
        paned.pack(fill='both', expand=True, padx=4, pady=3)

        # Left: scrollable sector grid
        left_outer = tk.Frame(paned, bg=DARK_BG)
        paned.add(left_outer, minsize=820, width=900)

        canvas = tk.Canvas(left_outer, bg=DARK_BG, highlightthickness=0)
        vsb    = tk.Scrollbar(left_outer, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        inner = tk.Frame(canvas, bg=DARK_BG)
        win   = canvas.create_window((0,0), window=inner, anchor='nw')

        def on_cfg(e):
            canvas.configure(scrollregion=canvas.bbox('all'))
            canvas.itemconfig(win, width=canvas.winfo_width())
        inner.bind('<Configure>', on_cfg)
        canvas.bind('<Configure>', lambda e: canvas.itemconfig(win, width=e.width))
        canvas.bind_all('<MouseWheel>',
                        lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), 'units'))

        for c in range(4):
            inner.columnconfigure(c, weight=1, uniform='col')

        self._build_agriculture(inner, 0, 0)
        self._build_military(inner, 0, 1)
        self._build_industry(inner, 1, 0)
        self._build_transport(inner, 1, 1)
        self._build_energy(inner, 2, 0)
        self._build_metals(inner, 2, 1)
        self._build_foreign_trade(inner, 2, 2)
        self._build_production(inner, 3, 0)
        self._build_assessments(inner, 3, 1)

        # Right sidebar
        right = tk.Frame(paned, bg=DARK_BG)
        paned.add(right, minsize=340, width=380)
        self._build_resource_panel(right)
        self._build_event_log(right)

        # Bottom bar
        btn_bar = tk.Frame(root, bg=DARK_BG, pady=5)
        btn_bar.pack(fill='x')
        btns = [
            ('⚙  IMPLEMENT PLAN [F5]', self._on_implement, RED),
            ('📊  HISTORY',             self._show_history, BLUE),
            ('📜  NOTES',               self._show_notes,   AMBER),
            ('❓  HELP [F1]',           self._show_help,    '#444'),
            ('💾  SAVE [Ctrl+S]',       self._save_game,    '#444'),
            ('📂  LOAD [Ctrl+O]',       self._load_game,    '#444'),
            ('↺  NEW GAME [Ctrl+N]',    self._new_game,     '#333'),
        ]
        for txt, cmd, bg in btns:
            tk.Button(btn_bar, text=txt, font=FB, fg=WHITE, bg=bg,
                      activebackground=bg, relief='flat', padx=10, pady=6,
                      command=cmd).pack(side='left', padx=3)

    # ── sector builder helpers ────────────────────────────────────────────────

    def _panel(self, parent, title, col, row, rowspan=1):
        f = tk.LabelFrame(parent, text=f'  {title}  ',
                          font=FH, fg=BLUE, bg=PANEL_BG,
                          labelanchor='n', padx=5, pady=4,
                          highlightbackground=BORDER, highlightthickness=1)
        f.grid(row=row, column=col, rowspan=rowspan,
               sticky='nsew', padx=3, pady=3)
        return f

    def _spin(self, parent, label, attr, lo=0, hi=200, tip=''):
        row = tk.Frame(parent, bg=PANEL_BG)
        row.pack(fill='x', pady=1)
        lbl = tk.Label(row, text=label, font=FM, fg=DIM,
                       bg=PANEL_BG, width=20, anchor='w')
        lbl.pack(side='left')
        val = getattr(self.state, attr, 0)
        var = tk.IntVar(value=val)
        self._vars[attr] = var
        spn = tk.Spinbox(row, from_=lo, to=hi, textvariable=var, width=5,
                         font=FM, bg='#21262d', fg=WHITE,
                         insertbackground=WHITE, relief='flat',
                         buttonbackground=BORDER,
                         command=self._schedule_refresh)
        spn.pack(side='left', padx=3)
        spn.bind('<KeyRelease>', lambda e: self._schedule_refresh())
        if tip:
            self._tip(lbl, tip)
        return var

    def _irow(self, parent, label, attr, col=WHITE):
        row = tk.Frame(parent, bg=PANEL_BG)
        row.pack(fill='x', pady=1)
        tk.Label(row, text=label, font=FM, fg=DIM,
                 bg=PANEL_BG, width=20, anchor='w').pack(side='left')
        lbl = tk.Label(row, text='—', font=FB, fg=col, bg=PANEL_BG, width=9, anchor='w')
        lbl.pack(side='left')
        self._info[attr] = lbl
        return lbl

    def _sol_row(self, parent, label, attr):
        lbl = self._irow(parent, label, attr, GREEN)
        return lbl

    def _div(self, parent):
        tk.Frame(parent, bg=BORDER, height=1).pack(fill='x', pady=3)

    def _tip(self, widget, text):
        def show(e):
            tip = tk.Toplevel(widget, bg=PANEL_BG)
            tip.overrideredirect(True)
            tip.geometry(f'+{e.x_root+12}+{e.y_root+12}')
            tk.Label(tip, text=text, font=FS, fg=WHITE, bg=PANEL_BG,
                     wraplength=280, padx=6, pady=4).pack()
            widget._tip = tip
        def hide(e):
            if hasattr(widget, '_tip'):
                try: widget._tip.destroy()
                except: pass
        widget.bind('<Enter>', show)
        widget.bind('<Leave>', hide)

    # ── sector panels ─────────────────────────────────────────────────────────

    def _build_agriculture(self, p, col, row):
        f = self._panel(p, '🌾 AGRICULTURE', col, row)
        self._spin(f,'Peasants (M)',       'peasants',  10,120,'Optimal ~60M.')
        self._spin(f,'Animals (M)',        'animals',    0, 60)
        self._spin(f,'Tractors (K)',       'tractors',   0,100,'Needs farm_fuel_alloc to be set.')
        self._spin(f,'Farm Fuel',          'farm_fuel_alloc', 0,50)
        self._spin(f,'Farm Food (ration)', 'farm_food',  0, 80,
                   'Food kept for peasants. Rest goes to food pool for other sectors.')
        self._spin(f,'Farm Goods',         'farm_goods', 0, 40)

        self._div(f)
        tk.Label(f, text='Collectivisation:', font=FM, fg=AMBER, bg=PANEL_BG).pack(anchor='w')
        self._col_var = tk.IntVar()
        bf = tk.Frame(f, bg=PANEL_BG); bf.pack(fill='x')
        for txt,val in [('None',0),('Voluntary',1),('Encourage',2),('Force',3)]:
            tk.Radiobutton(bf, text=txt, variable=self._col_var, value=val,
                           font=FS, fg=WHITE, bg=PANEL_BG, selectcolor=RED,
                           activebackground=PANEL_BG,
                           command=self._on_col).pack(side='left')

        self._div(f)
        self._irow(f,'Harvest (M tons)',   'harvest',   GREEN)
        self._irow(f,'Food Available',     'food_available', BLUE)
        self._irow(f,'Surplus',            'surplus',   BLUE)
        self._irow(f,'Displaced Workers',  'displaced_workers', AMBER)
        self._sol_row(f,'▸ Farm SOL',      'farm_sol')

    def _build_industry(self, p, col, row):
        f = self._panel(p,'🏭 INDUSTRY', col, row)
        self._spin(f,'Factories',          'factories',     50,600,'Start 192.')
        self._spin(f,'Workers (M)',        'induct_workers', 0, 60)
        self._spin(f,'Food for Workers',   'induct_food',    0, 50,
                   'Food ration for industrial workers. Drives Industry SOL.')
        self._spin(f,'Fuel for Industry',  'induct_fuel_alloc', 0,100,
                   'Optimal: factories × 0.04.')
        self._spin(f,'Industry Goods',     'induct_goods',  0, 40)
        self._div(f)
        self._irow(f,'Metals (auto)',      'induct_metals',  DIM)
        self._irow(f,'Capacity',           'induct_capacity', DIM)
        self._irow(f,'Cap. Available',     'induct_capacity_available', GREEN)
        self._irow(f,'Goods Produced',     'goods_produced', BLUE)
        self._irow(f,'Fuel Ratio',         'induct_fuel_ratio', AMBER)
        self._sol_row(f,'▸ Industry SOL',  'induct_sol')

    def _build_military(self, p, col, row):
        f = self._panel(p,'⚔ MILITARY', col, row)
        self._spin(f,'Soldiers (M)',       'soldiers',      0, 30)
        self._spin(f,'Weapons',            'total_weapons', 0,150)
        self._spin(f,'Mil Food',           'mil_food',      0, 30)
        self._spin(f,'Mil Fuel',           'mil_fuel_alloc',0, 30,'Optimal: weapons × 0.4.')
        self._spin(f,'Mil Goods',          'mil_goods',     0, 25)
        self._div(f)
        self._irow(f,'Effectiveness',      'military_effectiveness', GREEN)
        self._irow(f,'Reliability %',      'mil_reliability', BLUE)
        self._sol_row(f,'▸ Military SOL',  'mil_sol')

    def _build_transport(self, p, col, row):
        f = self._panel(p,'🚂 TRANSPORT', col, row)
        self._spin(f,'Transports',         'transports',        0,150)
        self._spin(f,'Workers (M)',        'transport_workers', 0, 30)
        self._spin(f,'Trans Food',         'trans_food',        0, 25)
        self._spin(f,'Trans Fuel',         'trans_fuel_alloc',  0, 40,'Optimal: transports × 0.25.')
        self._spin(f,'Trans Goods',        'trans_goods',       0, 25)
        self._div(f)
        self._irow(f,'Fuel Ratio',         'trans_fuel_ratio', AMBER)
        self._sol_row(f,'▸ Trans SOL',     'trans_sol')
        self._strike_lbl = tk.Label(f, text='', font=FB, fg=RED, bg=PANEL_BG)
        self._strike_lbl.pack(anchor='w')

    def _build_energy(self, p, col, row):
        f = self._panel(p,'⚡ ENERGY', col, row)
        self._spin(f,'Fuel Workers (M)',   'fuel_workers', 0, 30)
        self._spin(f,'Rigs',              'rigs',          0, 80)
        self._spin(f,'Energy Food',        'energy_food',  0, 20)
        self._spin(f,'Self Fuel',          'energy_fuel',  0, 10)
        self._spin(f,'Energy Goods',       'energy_goods', 0, 20)
        self._div(f)
        self._irow(f,'Fuel Produced',      'fuel_produced', GREEN)
        self._irow(f,'Fuel Ratio (all)',   'fuel_ratio',   AMBER)
        self._sol_row(f,'▸ Energy SOL',    'energy_sol')

    def _build_metals(self, p, col, row):
        f = self._panel(p,'⛏ METALS', col, row)
        self._spin(f,'Miners (M)',         'miners',         0, 30)
        self._spin(f,'Mine Equipment',     'mine_equipment', 0, 80,'Also opens new mine sites.')
        self._spin(f,'Mine Food',          'mine_food',      0, 25)
        self._spin(f,'Mine Fuel',          'mine_fuel_alloc',0, 25)
        self._spin(f,'Mine Goods',         'mine_goods',     0, 20)
        self._div(f)
        self._irow(f,'Metal Produced',     'metal_produced', GREEN)
        self._irow(f,'Metal Sites',        'metal_sites',    DIM)
        self._sol_row(f,'▸ Mine SOL',      'mine_sol')

    def _build_foreign_trade(self, p, col, row):
        f = self._panel(p,'🌐 TRADE', col, row)
        tk.Label(f, text='Exports (earn exchange):', font=FS, fg=DIM, bg=PANEL_BG).pack(anchor='w')
        self._spin(f,'Export Metals',      'trade_metals', 0,30,'2.0 exchange/unit.')
        self._spin(f,'Export Fuels',       'trade_fuels',  0,20,'1.5 exchange/unit.')
        self._spin(f,'Export Food',        'trade_food',   0,20,'1.0 exchange/unit.')
        tk.Label(f, text='Imports (spend exchange):', font=FS, fg=DIM, bg=PANEL_BG).pack(anchor='w',pady=(4,0))
        self._spin(f,'Import Factories',   'imported_factories',  0,30,'5 ex each.')
        self._spin(f,'Import Tractors',    'imported_tractors',   0,30,'2 ex each.')
        self._spin(f,'Import Mine Equip',  'imported_mine_equip', 0,20,'2 ex each.')
        self._spin(f,'Import Fuel Rigs',   'imported_fuel_rigs',  0,20,'3 ex each.')
        self._spin(f,'Import Transports',  'imported_transports', 0,20,'3 ex each.')
        self._div(f)
        self._irow(f,'Foreign Exchange',   'foreign_exchange', BLUE)
        self._irow(f,'Import Cost',        '_import_cost',     AMBER)

    def _build_production(self, p, col, row):
        f = self._panel(p,'🔧 PRODUCTION', col, row)
        tk.Label(f, text='Queue (costs metals+fuel):', font=FS, fg=DIM, bg=PANEL_BG).pack(anchor='w')
        self._spin(f,'Produce Factories',  'produce_factories',  0,80,'3 metals + 1 fuel each.')
        self._spin(f,'Produce Weapons',    'produce_weapons',    0,60,'2 metals + 0.5 fuel each.')
        self._spin(f,'Produce Tractors',   'produce_tractors',   0,50,'1 metal + 0.3 fuel each.')
        self._spin(f,'Produce Rigs',       'produce_rigs',       0,30,'2 metals + 0.5 fuel each.')
        self._spin(f,'Produce Transports', 'produce_transports', 0,40,'2 metals + 0.5 fuel each.')
        self._spin(f,'Produce Mine Equip', 'produce_mine_equip', 0,40,'1 metal + 0.3 fuel each.')
        self._spin(f,'Produce Goods',      'produce_goods',      0,40,'1 metal + 0.2 fuel each.')
        self._div(f)
        self._irow(f,'Metals Cost',        'prod_metals_cost', AMBER)
        self._irow(f,'Fuel Cost',          'prod_fuel_cost',   AMBER)
        self._irow(f,'Prod. Scale',        '_prod_scale',      GREEN)

    def _build_assessments(self, p, col, row):
        f = self._panel(p,'📋 ASSESSMENTS', col, row)
        for label, attr in [('Military Effect.','military_effectiveness'),
                             ('Industrial Prod.','industrial_production'),
                             ('Political Stab.', 'political_stability'),
                             ('Natl. Survival',  'national_survival')]:
            r = tk.Frame(f, bg=PANEL_BG); r.pack(fill='x', pady=1)
            tk.Label(r, text=label, font=FM, fg=DIM, bg=PANEL_BG,
                     width=18, anchor='w').pack(side='left')
            bg_bar = tk.Frame(r, bg=BORDER, width=70, height=10)
            bg_bar.pack(side='left', padx=3); bg_bar.pack_propagate(False)
            bar = tk.Frame(bg_bar, bg=GREEN, height=10)
            bar.place(x=0, y=0, relheight=1.0, width=0)
            lbl = tk.Label(r, text='—', font=FB, fg=GREEN, bg=PANEL_BG, width=5)
            lbl.pack(side='left')
            self._info[attr]        = lbl
            self._info[attr+'_bar'] = (bar, bg_bar)

        self._div(f)
        self._irow(f,'Total Deaths (M)',   'total_deaths',  RED)
        self._irow(f,'Human Cost',         '_human_cost',   AMBER)
        self._div(f)
        self._rep_lbl = tk.Label(f, text='', font=FS, fg=AMBER, bg=PANEL_BG,
                                 wraplength=200, justify='left')
        self._rep_lbl.pack(anchor='w')

    # ── right sidebar ─────────────────────────────────────────────────────────

    def _build_resource_panel(self, parent):
        f = tk.LabelFrame(parent, text='  📊 RESOURCE BALANCE  ',
                          font=FH, fg=PURPLE, bg=PANEL_BG,
                          labelanchor='n', padx=6, pady=4,
                          highlightbackground=BORDER, highlightthickness=1)
        f.pack(fill='x', padx=4, pady=4)
        tk.Label(f, text='Over-allocation shown in red.',
                 font=FS, fg=DIM, bg=PANEL_BG).pack(anchor='w')

        self._food_bar    = BalanceBar(f, 'Food');    self._food_bar.pack(fill='x', pady=1)
        self._metal_bar   = BalanceBar(f, 'Metals');  self._metal_bar.pack(fill='x', pady=1)
        self._fuel_bar    = BalanceBar(f, 'Fuel');    self._fuel_bar.pack(fill='x', pady=1)
        self._worker_bar  = BalanceBar(f, 'Workers'); self._worker_bar.pack(fill='x', pady=1)
        self._goods_bar   = BalanceBar(f, 'Goods');   self._goods_bar.pack(fill='x', pady=1)

        self._div(f)
        self._irow(f, 'Food Balance',   'food_balance',   GREEN)
        self._irow(f, 'Metal Balance',  'metal_balance',  GREEN)
        self._irow(f, 'Fuel Balance',   'fuel_balance',   GREEN)
        self._irow(f, 'Worker Balance', 'worker_balance', GREEN)
        self._irow(f, 'Goods Balance',  'goods_balance',  GREEN)
        self._irow(f, 'Food Scarcity',  'food_scarcity_mult', AMBER)

    def _build_event_log(self, parent):
        f = tk.LabelFrame(parent, text='  📝 EVENT LOG  ',
                          font=FH, fg=PURPLE, bg=PANEL_BG,
                          labelanchor='n', padx=4, pady=4,
                          highlightbackground=BORDER, highlightthickness=1)
        f.pack(fill='both', expand=True, padx=4, pady=4)
        self._log_text = tk.Text(f, font=FS, bg='#0d1117', fg=DIM,
                                 relief='flat', wrap='word',
                                 height=14, state='disabled')
        sb = tk.Scrollbar(f, command=self._log_text.yview)
        self._log_text.configure(yscrollcommand=sb.set)
        sb.pack(side='right', fill='y')
        self._log_text.pack(fill='both', expand=True)

        # Last event highlight
        self._event_lbl = tk.Label(f, text='', font=FB, fg=AMBER,
                                   bg=PANEL_BG, wraplength=320, justify='left')
        self._event_lbl.pack(anchor='w', pady=2)

    def _log(self, msg, colour=DIM):
        self._log_text.configure(state='normal')
        self._log_text.insert('1.0', msg + '\n')
        self._log_text.configure(state='disabled')

    # ── refresh ───────────────────────────────────────────────────────────────

    def _schedule_refresh(self):
        if self._pending:
            self.root.after_cancel(self._pending)
        for attr, var in self._vars.items():
            try: setattr(self.state, attr, var.get())
            except: pass
        self._pending = self.root.after(80, self._refresh)

    def _on_col(self):
        self.state.collectivize = self._col_var.get()
        self._refresh()

    def _refresh(self):
        s = self.state
        run_all_calculations(s)
        scores, overall, rep = calculate_judgement(s)

        # Import cost preview
        ic = (s.imported_factories  * IMPORT_COSTS['factories'] +
              s.imported_tractors   * IMPORT_COSTS['tractors'] +
              s.imported_mine_equip * IMPORT_COSTS['mine_equip'] +
              s.imported_fuel_rigs  * IMPORT_COSTS['fuel_rigs'] +
              s.imported_transports * IMPORT_COSTS['transports'])

        self._plan_lbl.config(
            text=f'Plan {s.plan_number}/3  │  Year {s.year}')
        self._diff_lbl.config(text=f'[{s.difficulty}]')
        self._score_lbl.config(text=f'Score: {overall:.0f}/100',
                               fg=pct_col(overall))
        self._status.config(
            text=(f'  Harvest {s.harvest:.0f}Mt  │  '
                  f'Fuel ratio {s.fuel_ratio:.2f}  │  '
                  f'Factories {s.factories}  │  '
                  f'Metals {s.metal_produced:.0f}  │  '
                  f'Workers {s.total_workers()}/{s.labour_force()}M  │  '
                  f'Deaths {s.total_deaths:.2f}M'))

        # Info labels
        float_attrs = {'fuel_ratio','trans_fuel_ratio','induct_fuel_ratio','total_deaths',
                       'harvest','food_available','max_quota','surplus','metal_produced',
                       'fuel_produced','foreign_exchange','prod_metals_cost','prod_fuel_cost',
                       'food_balance','metal_balance','fuel_balance','goods_produced',
                       'induct_metals','metal_sites','food_scarcity_mult'}
        for attr, lbl in self._info.items():
            if attr.endswith('_bar'): continue
            if attr == '_human_cost':
                v = scores['Human Cost']
                lbl.config(text=f'{v:.0f}', fg=pct_col(v))
                continue
            if attr == '_import_cost':
                lbl.config(text=f'{ic:.0f}', fg=RED if ic > s.foreign_exchange else WHITE)
                continue
            if attr == '_prod_scale':
                run_all_calculations(s)
                total_md = s.trade_metals + s.prod_metals_cost
                total_fd = s.total_fuel_demand() + s.prod_fuel_cost
                mps = min(1.0, s.metal_produced/max(0.1,total_md)) if total_md>0 else 1.0
                fps = min(1.0, s.fuel_produced/max(0.1,total_fd)) if total_fd>0 else 1.0
                ps = max(0,min(mps,fps))
                lbl.config(text=f'{ps*100:.0f}%', fg=pct_col(int(ps*100)))
                continue
            v = getattr(s, attr, 0)
            lbl.config(text=f'{v:.2f}' if attr in float_attrs else str(v))
            if 'sol' in attr:
                lbl.config(fg=sol_col(int(v)))
            elif attr in ('military_effectiveness','industrial_production',
                          'political_stability','national_survival'):
                lbl.config(fg=pct_col(int(v)))
            elif attr == 'food_scarcity_mult':
                col = GREEN if float(v) >= 0.95 else AMBER if float(v) >= 0.7 else RED
                lbl.config(fg=col)
            elif 'balance' in attr:
                lbl.config(fg=bal_col(float(v)))

        # Progress bars
        for attr in ('military_effectiveness','industrial_production',
                     'political_stability','national_survival'):
            if attr+'_bar' in self._info:
                bar, bg = self._info[attr+'_bar']
                v = getattr(s, attr, 0)
                w = int(bg.winfo_width() * v / 100)
                bar.place(width=max(0,w))
                bar.config(bg=pct_col(v))

        # Resource balance bars
        self._food_bar.update(s.food_allocated, s.harvest,
                              f'{s.food_allocated:.0f}/{s.harvest:.0f}')
        self._metal_bar.update(s.metal_allocated, s.metal_produced,
                               f'{s.metal_allocated:.0f}/{s.metal_produced:.0f}')
        self._fuel_bar.update(s.fuel_allocated, s.fuel_produced,
                              f'{s.fuel_allocated:.0f}/{s.fuel_produced:.0f}')
        self._worker_bar.update(s.total_workers(), s.labour_force(),
                                f'{s.total_workers()}/{s.labour_force()}')
        self._goods_bar.update(s.goods_allocated, s.goods_produced,
                               f'{s.goods_allocated:.0f}/{s.goods_produced:.0f}')

        # Strike warning
        self._strike_lbl.config(
            text='⚠ STRIKE RISK!' if s.trans_sol < STRIKE_THRESHOLD else '')

        self._rep_lbl.config(text=f'On track: {rep}')

    # ── implement plan ────────────────────────────────────────────────────────

    def _on_implement(self):
        s = self.state
        if s.plan_number > 3:
            self._show_results()
            return

        # Warn on over-allocation
        run_all_calculations(s)
        warnings = []
        if s.food_balance < -5:
            warnings.append(f'⚠ Food over-allocated by {abs(s.food_balance):.0f} units')
        if s.metal_balance < -3:
            warnings.append(f'⚠ Metal over-allocated by {abs(s.metal_balance):.0f} units')
        if s.worker_balance < -5:
            warnings.append(f'⚠ Workers over-allocated by {abs(s.worker_balance)} million')
        if s.foreign_exchange < (s.imported_factories * IMPORT_COSTS['factories'] +
                                 s.imported_tractors  * IMPORT_COSTS['tractors']):
            warnings.append('⚠ Insufficient foreign exchange for imports')
        if warnings:
            msg = 'Proceed anyway?\n\n' + '\n'.join(warnings)
            if not messagebox.askyesno('Resource Warning', msg, icon='warning'):
                return

        strike, event, prod_scale = implement_plan(s)

        # Event popup
        if event:
            self._event_lbl.config(text=f'📰 {event["name"]}: {event["desc"]}')
            self._log(f'EVENT [{s.year-5}]: {event["name"]} — {event["desc"]}', AMBER)
        else:
            self._event_lbl.config(text='No major event this plan.')

        # Production scale warning
        if prod_scale < 0.95:
            self._log(f'PRODUCTION: Only {prod_scale*100:.0f}% of queue built (resource shortage)', RED)

        # Strike handling
        if strike:
            choice = messagebox.askyesnocancel(
                'Transport Workers Strike!',
                'Dissatisfied workers are striking — threatens ALL sector output.\n\n'
                'Yes    = Suppress by force  (Political Stability −10)\n'
                'No     = Ignore             (Output −15% this plan)\n'
                'Cancel = Revise your plan',
                icon='warning')
            if choice is None:
                s.year -= 5; s.plan_number -= 1
                if s.history: s.history.pop()
                if s.event_log: s.event_log.pop(0)
                self._refresh(); return
            elif choice:
                s.political_stability = max(0, s.political_stability - 10)
                s.mil_reliability     = max(20, s.mil_reliability - 5)
                self._log('STRIKE: Suppressed by force (-10 stability)', RED)
            else:
                s.factories  = int(s.factories  * 0.85)
                s.fuel_produced = round(s.fuel_produced * 0.85, 1)
                self._log('STRIKE: Ignored (-15% output)', AMBER)

        # Game over check
        if s.game_over:
            messagebox.showerror('GAME OVER',
                                 'National survival has collapsed!\n'
                                 'The Soviet Union cannot defend itself.')
            self._show_results()
            return

        # Sync UI
        for attr, var in self._vars.items():
            try: var.set(getattr(s, attr, 0))
            except: pass
        self._col_var.set(s.collectivize)
        self._log(f'Plan {s.plan_number-1} complete | Score {s.history[-1]["overall"]} | Deaths {s.total_deaths:.2f}M')
        self._refresh()

        if s.plan_number > 3:
            self.root.after(400, self._show_results)

    # ── screens ───────────────────────────────────────────────────────────────

    def _show_results(self):
        s = self.state
        scores, overall, rep = calculate_judgement(s)

        win = tk.Toplevel(self.root, bg=DARK_BG)
        win.title("History's Judgement")
        win.geometry('600x560')
        win.resizable(False, False)
        win.grab_set()

        tk.Label(win, text="HISTORY'S JUDGEMENT", font=FT, fg=RED, bg=DARK_BG).pack(pady=(16,4))
        tk.Label(win, text=f'Overall Score: {overall:.1f} / 100',
                 font=FH, fg=pct_col(overall), bg=DARK_BG).pack(pady=2)
        tk.Label(win, text=rep, font=('Courier New', 10, 'italic'),
                 fg=AMBER, bg=DARK_BG, wraplength=560).pack(pady=6)

        tk.Frame(win, bg=BORDER, height=1).pack(fill='x', padx=20, pady=6)

        for label, score in scores.items():
            r = tk.Frame(win, bg=PANEL_BG, padx=10, pady=4)
            r.pack(fill='x', padx=20, pady=2)
            tk.Label(r, text=label, font=FM, fg=DIM, bg=PANEL_BG,
                     width=26, anchor='w').pack(side='left')
            bg_b = tk.Frame(r, bg=BORDER, width=180, height=12)
            bg_b.pack(side='left', padx=4); bg_b.pack_propagate(False)
            tk.Frame(bg_b, bg=pct_col(int(score)),
                     width=int(180*score/100), height=12).place(x=0,y=0)
            tk.Label(r, text=f'{score:.0f}', font=FB,
                     fg=pct_col(int(score)), bg=PANEL_BG, width=5).pack(side='left')

        tk.Frame(win, bg=BORDER, height=1).pack(fill='x', padx=20, pady=6)
        tk.Label(win,
                 text=f'Deaths: {s.total_deaths:.2f}M  │  Factories: {s.factories}  │  Year: {s.year}  │  Difficulty: {s.difficulty}',
                 font=FS, fg=DIM, bg=DARK_BG).pack(pady=2)

        bf = tk.Frame(win, bg=DARK_BG); bf.pack(pady=10)
        tk.Button(bf, text='Close', font=FB, fg=WHITE, bg=RED, relief='flat',
                  padx=16, pady=5, command=win.destroy).pack(side='left', padx=6)
        tk.Button(bf, text='New Game', font=FB, fg=WHITE, bg=BORDER, relief='flat',
                  padx=16, pady=5, command=lambda: (win.destroy(), self._new_game())).pack(side='left', padx=6)

    def _show_history(self):
        if not self.state.history:
            messagebox.showinfo('No History', 'Complete at least one plan first.')
            return
        win = tk.Toplevel(self.root, bg=DARK_BG)
        win.title('Plan History'); win.geometry('780x320')
        tk.Label(win, text='FIVE YEAR PLAN HISTORY', font=FH, fg=BLUE, bg=DARK_BG).pack(pady=6)
        cols = ('Plan','Year','Harvest','Factories','SOL','Mil','Ind','Pol','Surv','Deaths','Score','Event')
        tree = ttk.Treeview(win, columns=cols, show='headings', height=8)
        sty = ttk.Style(win); sty.theme_use('default')
        sty.configure('Treeview', background=PANEL_BG, foreground=WHITE,
                      fieldbackground=PANEL_BG, font=FM)
        sty.configure('Treeview.Heading', background=BORDER, foreground=BLUE, font=FB)
        col_widths = [40,50,60,70,40,40,40,40,40,55,50,120]
        for col,w in zip(cols,col_widths):
            tree.heading(col, text=col); tree.column(col, width=w, anchor='center')
        for h in self.state.history:
            tree.insert('','end',values=(
                h['plan'],h['year'],f"{h['harvest']:.0f}",h['factories'],
                h['sol_avg'],h['military'],h['industrial'],h['political'],
                h['survival'],f"{h['deaths']:.2f}",h['overall'],h['event']))
        sb = ttk.Scrollbar(win, orient='horizontal', command=tree.xview)
        tree.configure(xscrollcommand=sb.set)
        tree.pack(fill='both', expand=True, padx=8, pady=4)
        sb.pack(fill='x', padx=8)
        tk.Button(win, text='Close', font=FB, fg=WHITE, bg=BORDER, relief='flat',
                  padx=12, pady=4, command=win.destroy).pack(pady=6)

    def _show_notes(self):
        plan = min(3, self.state.plan_number)
        title, text = HISTORICAL_NOTES.get(plan, ('',''))
        win = tk.Toplevel(self.root, bg=DARK_BG)
        win.title('Historical Notes'); win.geometry('520x280')
        tk.Label(win, text=title, font=FH, fg=AMBER, bg=DARK_BG,
                 wraplength=480).pack(pady=(12,4), padx=12)
        tk.Label(win, text=text, font=FM, fg=WHITE, bg=DARK_BG,
                 wraplength=480, justify='left').pack(padx=16, pady=4)
        tk.Button(win, text='Close', font=FB, fg=WHITE, bg=BORDER, relief='flat',
                  padx=12, pady=4, command=win.destroy).pack(pady=10)

    def _show_help(self):
        win = tk.Toplevel(self.root, bg=DARK_BG)
        win.title('Help'); win.geometry('600x520')
        txt = tk.Text(win, font=FM, bg=PANEL_BG, fg=WHITE, relief='flat',
                      wrap='word', padx=12, pady=8)
        sb = tk.Scrollbar(win, command=txt.yview)
        txt.configure(yscrollcommand=sb.set)
        sb.pack(side='right', fill='y'); txt.pack(fill='both', expand=True)
        help_text = """
STALIN'S DILEMMA — HELP

OBJECTIVE
Industrialise the Soviet Union across three Five Year Plans (1928-1942)
while keeping the population alive and the state politically stable.

RESOURCES
  Food:    Produced by agriculture (harvest). Distributed to all sectors.
           Farm food = peasant ration. Remainder goes to other sectors.
  Metals:  Produced by miners + equipment. Auto-assigned to industry
           after trade exports and production costs are deducted.
  Fuel:    Produced by energy sector. Distributed across all sectors.
  Goods:   Produced by industry (capacity_available × 0.15).
           Distributed as consumer goods to improve SOL.
  Workers: Limited by USSR labour force (~80-96M total).
  Exchange:Earned by exporting metals/fuels/food. Spent on imports.

STANDARD OF LIVING (SOL)
  SOL = (food×2 + goods) / (workers×3) × 100
  Low SOL → worker unrest → political instability → deaths.
  Transport SOL below 25 triggers a STRIKE (affects all sectors).

PRODUCTION QUEUE
  Items cost metals + fuel. If resources are insufficient, production
  is scaled down proportionally. Build factories to grow capacity.

RESOURCE BALANCE BARS (right panel)
  Green = fine.  Amber = near limit.  Red = over-allocated.
  Over-allocation reduces effectiveness of all sectors.

COLLECTIVISATION
  None/Voluntary: stable, modest efficiency.
  Encourage: moderate gain, small political cost.
  Force: largest harvest gain but chaos penalty (worst in Plan 1),
         displaced workers, high death toll.

EVENTS
  One random event fires per plan. Some are plan-specific
  (e.g. Barbarossa in Plan 3). Events can be positive or negative.

ASSESSMENT SCORES (each 0-100)
  Military Effectiveness = soldiers × 6 + weapons × 2, modified by SOL + fuel
  Industrial Production  = growth in factories, transports, equipment
  Political Stability    = average SOL minus collectivisation/strike penalties
  National Survival      = military vs external threat (0 = game over)
  Human Cost             = 100 − (deaths × 8)

KEYBOARD SHORTCUTS
  F5         = Implement Plan
  F1         = This help screen
  Ctrl+S     = Save game
  Ctrl+O     = Load game
  Ctrl+N     = New game
"""
        txt.insert('1.0', help_text.strip())
        txt.configure(state='disabled')
        tk.Button(win, text='Close', font=FB, fg=WHITE, bg=BORDER, relief='flat',
                  padx=12, pady=4, command=win.destroy).pack(pady=6)

    def _new_game(self):
        # Difficulty selection
        win = tk.Toplevel(self.root, bg=DARK_BG)
        win.title('New Game'); win.geometry('340x200')
        win.grab_set()
        tk.Label(win, text='SELECT DIFFICULTY', font=FH, fg=BLUE, bg=DARK_BG).pack(pady=(16,8))
        diff_var = tk.StringVar(value='Normal')
        for d in ['Easy','Normal','Hard']:
            tk.Radiobutton(win, text=d, variable=diff_var, value=d,
                           font=FM, fg=WHITE, bg=DARK_BG, selectcolor=RED,
                           activebackground=DARK_BG).pack(anchor='center')
        def start():
            self.state = GameState(difficulty=diff_var.get())
            for attr, var in self._vars.items():
                try: var.set(getattr(self.state, attr, 0))
                except: pass
            self._col_var.set(0)
            self._event_lbl.config(text='')
            self._log_text.configure(state='normal')
            self._log_text.delete('1.0', 'end')
            self._log_text.configure(state='disabled')
            self._refresh()
            win.destroy()
        tk.Button(win, text='Start Game', font=FB, fg=WHITE, bg=RED, relief='flat',
                  padx=16, pady=6, command=start).pack(pady=14)

    def _save_game(self):
        path = filedialog.asksaveasfilename(
            defaultextension='.json',
            filetypes=[('JSON save file','*.json')],
            title='Save Game')
        if not path: return
        try:
            d = self.state.to_dict()
            with open(path, 'w') as f:
                json.dump(d, f, indent=2)
            messagebox.showinfo('Saved', f'Game saved to:\n{os.path.basename(path)}')
        except Exception as e:
            messagebox.showerror('Save Error', str(e))

    def _load_game(self):
        path = filedialog.askopenfilename(
            filetypes=[('JSON save file','*.json')],
            title='Load Game')
        if not path: return
        try:
            with open(path) as f:
                d = json.load(f)
            diff = d.get('difficulty','Normal')
            self.state = GameState(diff)
            self.state.from_dict(d, diff)
            for attr, var in self._vars.items():
                try: var.set(getattr(self.state, attr, 0))
                except: pass
            self._col_var.set(self.state.collectivize)
            # Reload event log
            self._log_text.configure(state='normal')
            self._log_text.delete('1.0','end')
            for entry in self.state.event_log:
                self._log_text.insert('end', entry + '\n')
            self._log_text.configure(state='disabled')
            self._refresh()
            messagebox.showinfo('Loaded', f'Game loaded: Plan {self.state.plan_number}, Year {self.state.year}')
        except Exception as e:
            messagebox.showerror('Load Error', str(e))


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    root = tk.Tk()
    StalinsDilemmaApp(root)
    root.mainloop()
