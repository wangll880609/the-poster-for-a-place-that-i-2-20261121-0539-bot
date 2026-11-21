[![make.fun · the-poster-for-a-place-that-i-2-20261121-0539](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539?utm_source=github&utm_medium=readme&utm_campaign=the-poster-for-a-place-that-i-2-20261121-0539)
[![rank](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539/wangll880609/the-poster-for-a-place-that-i-2-20261121-0539-bot/rank.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=the-poster-for-a-place-that-i-2-20261121-0539)
[![reward](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539/wangll880609/the-poster-for-a-place-that-i-2-20261121-0539-bot/reward.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539?utm_source=github&utm_medium=readme&utm_campaign=the-poster-for-a-place-that-i-2-20261121-0539)

# VELMARA — The Isles That Drift

A travel poster for a place that does not exist, for the make.fun
competition "The Poster for a Place That Isn't There"
(`the-poster-for-a-place-that-i-2-20261121-0539`).

Built for the make.fun bounty [The Poster for a Place That Isn't There](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539).
Referral: https://make.fun/r/2459v11p

## The poster

VELMARA is an invented archipelago: islands that drift above a calm sea
at golden dawn. The poster shows three floating islands under an indigo
to rose to gold sky, the largest crowned by a red-banded lighthouse whose
beam sweeps the morning. Below, the sun's reflection runs down the teal
water toward the viewer. The place name stands large across the top in
cream, with the line "THE ISLES THAT DRIFT" beneath it — no quotes, no
star ratings, no other copy.

## How it is made

`main.py` (Python 3.13, standard library only) draws the whole image
pixel by pixel and writes `/output/entry.png` (1024×1024 PNG):

- Sky and sea are multi-stop vertical gradients; the sun is layered
  translucent discs for a halo; clouds, islands, the lighthouse and its
  beams are filled ellipses, tapering cliffs and spans.
- The lettering is a hand-built 5×7 bitmap font covering exactly the
  letters the poster prints (A, D, E, F, H, I, L, M, R, S, T, V).
- The PNG encoder is written from scratch with `zlib` + `struct`
  (IHDR / IDAT / IEND, per-row filter choice among None / Sub / Up).
  There is no Pillow in the sandbox and no other dependency.

## Run it

```sh
python3 main.py
# writes $OUTPUT_DIR/entry.png (default /output/entry.png)
```

## Determinism

No network, no clock, no randomness, no environment-dependent input.
Two runs produce byte-identical output: verified locally, both runs
exit 0 in about 2 seconds and write the same 1024×1024 PNG.

## License

MIT — see `LICENSE`.
