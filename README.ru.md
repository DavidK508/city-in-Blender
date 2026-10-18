# city-in-Blender

> Этот проект создан нейросетью.
> **[README in English](README.md)**

Процедурный генератор мегаполиса для Blender 5.x (headless, Python API).

## Требования

- Blender 5.x (`blender` в PATH, можно переопределить через `BLENDER=...`)

## Запуск

```bash
make preview        # превью день   -> renders/preview.png
make preview-night  # превью ночь   -> renders/preview_night.png
make render         # финал 1920x1080 -> renders/city.png
make anim           # пролёт камеры -> renders/city_anim.mp4
make save           # сохранить .blend -> renders/city.blend
```

Или напрямую через Blender:

```bash
blender --background --python run.py -- --preview --seed 7 --night
```

Флаги: `--seed N`, `--night`, `--preview`, `--render`, `--anim`, `--frames N`,
`--save`, `--out PATH`.

## Как это устроено

| Модуль | Роль |
|---|---|
| `city/roads.py` | джиттерная сетка улиц (артерии + местные), тротуары, земля |
| `city/buildings.py` | деление лотов, здания с подиумами/сужением/антеннами, геометрические окна и балконы, высоты по расстоянию до центра |
| `city/materials.py` | процедурные фасады, стеклянные окна с ночным свечением, материалы балконов и перил |
| `city/details.py` | фонари, машины (колёса, фары и задние фонари), деревья (парки + тротуары) |
| `city/lighting.py` | небо + солнце (день) / луна + тёплые окна (ночь), bloom-композитор |
| `city/camera.py` | статичный кадр или анимированный пролёт к даунтауну |
| `city/main.py` | CLI, сборка сцены, рендер |

Вся случайность детерминирована сидом (`--seed`): одинаковый seed → одинаковый город.
