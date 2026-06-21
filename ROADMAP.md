# Roadmap — RTS Unit Generator

_Status: active · updated 2026-05-30_

A Python tool that procedurally generates 3D vehicle models and renders them as
2D isometric sprite sheets — the asset-generation companion to the Ridgeline
RTS engine (sibling `2D_RTS`), which consumes the sprites.

## Shipped

- [x] Procedural vehicle generation — tanks, APCs, artillery
- [x] Parameterized geometry (seed, hull dimensions, turret size, barrel length)
- [x] Two-color rendering (hull color + gray mechanical detail)
- [x] 8-direction isometric sprite sheets (512×512) with pivot + muzzle metadata
- [x] GLB 3D mesh export with split animated parts (hull / turret / barrel / mobility)
- [x] Sprite animation sequences (idle, firing, moving) with per-frame transforms
- [x] GUI app — vehicle list, color picker, real-time azimuth/elevation preview, batch + progress
- [x] CLI pipeline / programmatic API
- [x] Config + preset save/load
- [x] Debug visualization (13 camera angles, coordinate-axis overlays)
- [x] JSON metadata export (sprite map, pivots, muzzle positions, animation)
- [x] Interactive preview (build model once, render on-demand at any angle)

## Next

- [ ] More animation variants (combat / movement)
- [ ] Optimize rendering for large batch exports
- [ ] Direct export to game-asset formats (atlas + animation configs) for Ridgeline

## Backlog

- [ ] More unit types — aircraft, naval, infantry, buildings
- [ ] Advanced rendering — particle effects, texture variants, normal maps
- [ ] GUI — 3D preview window, drag-and-drop editing, batch templates
- [ ] Performance — multi-threaded / GPU rendering, caching
- [ ] Game-engine plugins / asset-pipeline integration
