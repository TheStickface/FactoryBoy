# src/loader.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import yaml


@dataclass
class Recipe:
    name: str
    ingredients: dict[str, float]
    products: dict[str, float]
    crafting_time: float
    machine: str
    surface: str


@dataclass
class Tier:
    name: str
    target_hours: Optional[float]
    science_packs: dict[str, int]
    unlocks: list[str]


@dataclass
class Config:
    root_input: str
    root_input_rate: float
    machine_speeds: dict[str, float]
    bottleneck_threshold: int
    machine_budget: dict[str, dict[str, int]]
    spoilage_multiplier: float
    perishable_items: list[str]
    default_target_hours: dict[str, float]
    report_output: str


@dataclass
class GameData:
    recipes: dict[str, Recipe]
    tiers: list[Tier]
    config: Config


def load_data(data_dir: str) -> GameData:
    path = Path(data_dir)
    config = _load_config(path / "config.yaml")
    recipes = _load_recipes(path / "recipes.yaml")
    tiers = _load_tech_tree(path / "tech_tree.yaml")
    return GameData(recipes=recipes, tiers=tiers, config=config)


def _load_config(path: Path) -> Config:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Config(
        root_input=raw["root_input"],
        root_input_rate=float(raw["root_input_rate"]),
        machine_speeds={k: float(v) for k, v in raw["machine_speeds"].items()},
        bottleneck_threshold=int(raw["bottleneck_threshold"]),
        machine_budget={
            surface: {k: int(v) for k, v in stage_budget.items()}
            for surface, stage_budget in raw["machine_budget"].items()
        },
        spoilage_multiplier=float(raw.get("spoilage_multiplier", 1.0)),
        perishable_items=raw.get("perishable_items", []),
        default_target_hours={k: float(v) for k, v in raw["default_target_hours"].items()},
        report_output=raw["report_output"],
    )


def _load_recipes(path: Path) -> dict[str, Recipe]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    recipes = {}
    for name, data in (raw.get("recipes") or {}).items():
        recipes[name] = Recipe(
            name=name,
            ingredients={k: float(v) for k, v in data["ingredients"].items()},
            products={k: float(v) for k, v in data["products"].items()},
            crafting_time=float(data["crafting_time"]),
            machine=data["machine"],
            surface=data.get("surface", "nauvis"),
        )
    return recipes


def _load_tech_tree(path: Path) -> list[Tier]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    tiers = []
    for data in (raw.get("tiers") or []):
        target_hours = data.get("target_hours")
        tiers.append(Tier(
            name=data["name"],
            target_hours=float(target_hours) if target_hours is not None else None,
            science_packs={k: int(v) for k, v in data["science_packs"].items()},
            unlocks=data.get("unlocks", []),
        ))
    return tiers
