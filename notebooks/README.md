# Notebooks / Cuadernos

The didactic layer of Contraste: notebooks that teach, step by step and on the product's own committed data, how the validation
tests of the engine [`riskvalidation`](https://github.com/fsantibanezleal/CAOS_RiskValidation) work, where each method stands
against the state of the art and what Contraste adds beyond it. They import the engine and the pipeline's readers and never
re-implement a method. The rule is CAOS_MANAGE `conventions/product-notebooks.md`, carried by the product template from release
0.10.000.

La capa didáctica de Contraste: cuadernos que enseñan, paso a paso y con los datos versionados del propio producto, cómo
funcionan las pruebas de validación del motor `riskvalidation`, dónde queda cada método frente al estado del arte y qué agrega
Contraste más allá. Importan el motor y los lectores del pipeline y nunca reimplementan un método.

## The two trees / Los dos árboles

| Language | Index | Folder |
|---|---|---|
| English | [en/README.md](en/README.md) | [en/](en/) |
| Español | [es/README.md](es/README.md) | [es/](es/) |

The two trees hold the same notebooks at the same relative paths (the names are English, so the mirror is checkable); each
notebook is written wholly in its tree's language, with the same code and the same numbers. Topics run from simple to complex,
and notebooks inside a topic by level: 1 fundamentals, 2 the method in practice, 3 state of the art, 4 beyond the state of the art.
Every notebook opens with its title, level, prerequisites and reading time, and follows the same sections: Objectives, Setup, Data,
Method, Results, Summary and References (the state of the art at level 3 and 4, and what goes beyond it at level 4).

Los dos árboles tienen los mismos cuadernos en las mismas rutas relativas (los nombres están en inglés, así que el espejo se puede
comprobar); cada cuaderno está escrito entero en el idioma de su árbol, con el mismo código y los mismos números.

## Install and run them / Instalar y correrlos

```bash
./scripts/setup.sh --notebooks             # builds .venv-notebooks from notebooks/requirements.txt (setup.ps1 -Notebooks on Windows)
python scripts/run_notebooks.py            # executes every notebook top to bottom in a fresh kernel and writes the outputs in place
python scripts/run_notebooks.py --check    # executes copies, writes nothing, fails on any error or on outputs that differ from a fresh run
python scripts/check_notebooks.py          # the static check: layout, mirror, levels, anatomy, metadata, clean, pins (CI and local)
```

The environment is the familiar one: `pip install -r notebooks/requirements.txt` in a virtual environment. Its first line is the
engine, `riskvalidation==0.8.0`, from PyPI; the other lines are the method libraries at the pins of `data-pipeline/requirements.txt`
and the runtime that executes the notebooks. Only the runner writes a notebook's outputs; the committed notebooks are the
runner's output. To read one, open it on GitHub or in any Jupyter client (select the `.venv-notebooks` kernel to run it). A
notebook reads committed files only (`data/derived/` and `data/examples/`): it needs no raw data and no `CONTRASTE_DATA`, and it
writes nothing into the repository.

### The maintainer's route until the PyPI release

`riskvalidation` 0.8.0 is the engine release `v0.08.000` and is not published on PyPI yet (backlog BL-039: the owner registers the
trusted publisher first), so the pin `riskvalidation==0.8.0` does not resolve from the public index today. The maintainers, who
have access to the engine repository, build the wheel of that release tag once and let pip find it there:

```bash
git clone --depth 1 --branch v0.08.000 <the engine repository> <engine folder>
python -m pip wheel --no-deps -w <wheel folder> <engine folder>
python -m pip install --find-links <wheel folder> -r notebooks/requirements.txt
```

This changes nothing in a notebook or in `requirements.txt`: the pin is the PyPI one, and the Contraste release that carries the
set ships after the PyPI publication, when the plain `pip install -r notebooks/requirements.txt` works for everyone.

## Topics / Temas

The map has 14 topics; each lands with its own unit, and an index lists a topic's folder as soon as it exists. Today topic 01 is
here: [en/01-getting-started/](en/01-getting-started/) and [es/01-getting-started/](es/01-getting-started/).

## Beyond the state of the art / Más allá del estado del arte

The SDD claims eight components in its section `## Beyond the state of the art` (BS-1 to BS-8), each with its committed evidence.
Every claim gets a level 4 notebook in each language with its topic's unit; until then the static check reports the claim as covered
by no level 4 notebook, and `tests/test_notebooks_layer.py` names the claims that are pending.
