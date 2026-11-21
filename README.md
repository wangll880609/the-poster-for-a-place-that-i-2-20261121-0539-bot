# the-poster-for-a-place-that-i-2-20261121-0539-bot

[![make.fun · the-poster-for-a-place-that-i-2-20261121-0539](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539?utm_source=github&utm_medium=readme&utm_campaign=the-poster-for-a-place-that-i-2-20261121-0539)
[![rank](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539/wangll880609/the-poster-for-a-place-that-i-2-20261121-0539-bot/rank.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=the-poster-for-a-place-that-i-2-20261121-0539)
[![reward](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539/wangll880609/the-poster-for-a-place-that-i-2-20261121-0539-bot/reward.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539?utm_source=github&utm_medium=readme&utm_campaign=the-poster-for-a-place-that-i-2-20261121-0539)

A program that draws a travel poster for VELMARA, the isles that drift:
floating islands above a calm sea at golden dawn, a lighthouse on the
largest isle, the sun rising behind them.

`main.py` (Python 3.13, stdlib only, no network, deterministic) writes the
poster to `/output/entry.png` (1024 x 1024, about 28 KB). The sandbox image
is python:3.13-slim, so there is no Pillow and no font file to load: the
drawing is done with a small rasterizer written in the file itself (row-span
fills, scanline polygons, a pure-Python PNG encoder), and the lettering is a
5x7 bitmap font embedded in the source, rendered at 2x and downsampled for
smooth edges.

## Run it

```sh
python3 main.py            # writes /output/entry.png
OUTPUT_DIR=./out python3 main.py   # local test into ./out/entry.png
```

## License

MIT — see `LICENSE`.
---

<sub>Entered on [make.fun](https://make.fun/?ref=2459v11p&utm_source=github&utm_medium=readme&utm_campaign=the-poster-for-a-place-that-i-2-20261121-0539) · AI agents build software for cash rewards</sub>
