# Lunar launchers by Santi Herranz

Rail launchers on the Moon. An electromagnetic rail (a mass driver) runs on solar power and needs no propellant. On the Moon there is no air, and escape speed is only 2.38 km/s, so a rail a few kilometres long is enough to throw payloads into orbit or across the surface.

This repository has three pieces of the same lunar supply chain:

| | Piece | What it does |
|---|---|---|
| 1 | [**Polar ice hop**](polar-ice-hop/) | A rail on a sunlit ridge at the south pole throws blocks of ice cut from permanently shadowed craters on a 2,728 km ballistic arc to the equator. The blocks land beside the oxygen rail and resupply its plant with water. |
| 2 | [**Lunar oxygen to L1**](oxygen-to-l1/) | Oxygen is extracted from the regolith at the equator, liquefied, and launched in 500 kg capsules to the Earth–Moon L1 point. A depot there refuels ships bound for Mars. |
| 3 | [**L1 Oxygen Run**](game/), a game | One button. Fire a capsule at the right speed and see whether it reaches the depot at L1. You choose between the flat rail and the hillside rail. **[Play it in your browser](https://santiherranz.github.io/lunar-launchers/game/)** |

![Lunar oxygen to L1: the flat-rail poster](oxygen-to-l1/plates/lunar_l1_poster.jpg)

![Polar ice by rail](polar-ice-hop/plates/salto_polar.jpg)

## Key numbers

| | Polar ice hop | Oxygen to L1 (flat rail) | Oxygen to L1 (hillside rail) |
|---|---|---|---|
| Site | −89.5°, 0° (near Shackleton) → 0.0°, 84.92°W | 2.75°N 14.25°W | 0.0°, 84.92°W, rail at 30° on a 1,381 m slope |
| Launch speed | 1,543 m/s | 2,328.2 m/s | 2,327.3 m/s |
| Rail | 1.2 km at 100 g | 2.76 km at 100 g | 2.76 km at 100 g, inclined 30° |
| Flight | 49 min, ballistic | 308 h, with one loop around the Moon | 59 h, direct |
| Payload | 940 kg ice block, impacts at 1,546 m/s | 356 kg of liquid oxygen delivered | 372 kg of liquid oxygen delivered |
| Aim | 6.1 km per m/s of error | 5,730 km per m/s, corrected at T+24 h | 1,925 km per m/s, corrected at T+24 h |

## What's inside

Each folder has its own README with the reference figures, the main findings and how to rerun the calculations.

- `*/calculations/`: the Python models (NumPy and SciPy). Each script writes its `.json` or `.log` next to it, and the outputs committed here are the reference runs. **Script names, comments and output keys are in Spanish**, the language the work was done in. The READMEs explain each script in English.
- `*/plates/`: the illustrated plates, drawn entirely in code. Only the rendered images are published, not the drawing engine.
- `game/index.html`: a single self-contained page with no build step.

## Licence

Code: [MIT](LICENSE). Plates and illustrations: [CC BY 4.0](LICENSE-images.md). Please credit Santi Herranz.
