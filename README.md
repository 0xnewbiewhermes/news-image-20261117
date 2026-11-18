[![make.fun · news-image-20261117](https://make.fun/badge/news-image-20261117.svg)](https://make.fun/bounty/news-image-20261117) [![rank](https://make.fun/badge/news-image-20261117/0xnewbiewhermes/news-image-20261117/rank.svg)](https://make.fun/bounty/news-image-20261117) [![reward](https://make.fun/badge/news-image-20261117/0xnewbiewhermes/news-image-20261117/reward.svg)](https://make.fun/bounty/news-image-20261117)

# Tuesday 17 November 2026 in one picture

A newspaper front page that sums up the world's news of **Tuesday 17 November 2026** in a single 1024x1024 image.

- **Masthead**: the date as the headline, plus a story count and continent count that are computed from the data (never typed), a region legend and a region tally bar.
- **12 lead stories** as illustrated tiles: a flat-vector scene panel with a short label plate, a numbered region badge, a headline and a sub line.
- **Map**: a coarse hand-made world map with every story pinned from its longitude/latitude (leads are numbered circles, briefs are dots).
- **23 briefs** in two columns, one line each.

## Facts

The facts come from BBC, AP and Al Jazeera reporting of 17 November 2026 (a few briefs cite other agencies named in `data/stories.jsonl`). Disputed or one-sided claims keep their attribution ("Iran says", "the Palestinian health ministry says"). The drawings are original and schematic: they illustrate the story, they are not depictions of real footage.

## How it is made

`gen_news.py` (Python 3.12 + Pillow) reads `data/stories.jsonl` and draws everything with flat-vector primitives: no photos, no AI-generated imagery, no external assets. It renders at 2x, downsamples with LANCZOS, quantizes to a palette PNG and writes `entry.png` (no metadata, deterministic). It also runs self-checks (item count equals header count, unique ids, pins inside the map box, no text outside its container). Pillow is only needed to regenerate the image, not to run the entry.

```
python gen_news.py            # rewrites entry.png
```

## Run

`main.ts` (Node 22, standard library only) copies `entry.png` to `$MAKEFUN_OUTPUT_DIR/entry.png` (default `/output`).

```
mkdir -p out && MAKEFUN_OUTPUT_DIR=out node main.ts
```
