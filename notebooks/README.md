# Notebooks / Cuadernos

The didactic layer of Contraste: notebooks that teach, step by step and on the product's own committed data, how the validation
tests of the engine [`riskvalidation`](https://github.com/fsantibanezleal/CAOS_RiskValidation) work, how each method compares
with the published methods and what Contraste proposes of its own. They import the engine and the pipeline's readers and never
re-implement a method. The rule is CAOS_MANAGE `conventions/product-notebooks.md`, carried by the product template from release
0.10.000.

La capa didáctica de Contraste: cuadernos que enseñan, paso a paso y con los datos versionados del propio producto, cómo
funcionan las pruebas de validación del motor `riskvalidation`, cómo se compara cada método con los métodos publicados y qué
propone Contraste. Importan el motor y los lectores del pipeline y nunca reimplementan un método.

## The two trees / Los dos árboles

| Language | Index | Folder |
|---|---|---|
| English | [en/README.md](en/README.md) | [en/](en/) |
| Español | [es/README.md](es/README.md) | [es/](es/) |

The two trees hold the same notebooks at the same relative paths (the names are English, so the mirror is checkable); each
notebook is written wholly in its tree's language (prose, comments, labels and printed text), with the same cells, the same code
structure and the same numbers. What the engine and the documents carry as identifiers or as their own texts (a `test_id`, a key, a
light, a null hypothesis, a reference) is printed as it is written there, in English, in both trees; the bilingual fields of the
documents are read in the tree's language. Topics run from simple to complex,
and notebooks inside a topic by level: 1 fundamentals, 2 the method in practice, 3 comparison with published methods, 4 proposed methods.
Every notebook opens with its title, level, prerequisites and reading time, and follows the same sections: Objectives, Setup, Data,
Method, Results, Summary and References (Comparison at levels 3 and 4, and Evidence at level 4).

Los dos árboles tienen los mismos cuadernos en las mismas rutas relativas (los nombres están en inglés, así que el espejo se puede
comprobar); cada cuaderno está escrito entero en el idioma de su árbol (prosa, comentarios, etiquetas y texto impreso), con las mismas celdas, la
misma estructura de código y los mismos números. Lo que el motor y los documentos traen como identificadores o como textos propios
(un `test_id`, una clave, una luz, una hipótesis nula, una referencia) se imprime tal como allí está escrito, en inglés, en ambos
árboles; los campos bilingües de los documentos se leen en el idioma del árbol.

## Install and run them / Instalar y correrlos

```bash
./scripts/setup.sh --notebooks             # builds .venv-notebooks from notebooks/requirements.txt (setup.ps1 -Notebooks on Windows)
python scripts/run_notebooks.py            # executes every notebook top to bottom in a fresh kernel and writes the outputs in place
python scripts/run_notebooks.py --check    # executes copies, writes nothing, fails on any error or on outputs that differ from a fresh run
python scripts/check_notebooks.py          # the static check: layout, mirror, levels, anatomy, metadata, clean, pins (CI and local)
```

The environment is the familiar one: `pip install -r notebooks/requirements.txt` in a virtual environment. Its first line is the
engine, `riskvalidation==1.1.0`, from PyPI; the other lines are the method libraries at the pins of `data-pipeline/requirements.txt`
and the runtime that executes the notebooks. Only the runner writes a notebook's outputs; the committed notebooks are the
runner's output. To read one, open it on GitHub or in any Jupyter client (select the `.venv-notebooks` kernel to run it). A
notebook reads committed files only (`data/derived/` and `data/examples/`): it needs no raw data and no `CONTRASTE_DATA`, and it
writes nothing into the repository.

## Topics / Temas

The map has 14 topics; each lands with its own unit, and an index lists a topic's folder as soon as it exists. Today topic 01 is
here: [en/01-getting-started/](en/01-getting-started/) and [es/01-getting-started/](es/01-getting-started/).

## What the product claims / Lo que afirma el producto

Each claim of the SDD has a level 4 notebook in each language that demonstrates it; the index of each tree lists the claims with
their notebooks ([en/README.md](en/README.md), [es/README.md](es/README.md)), and the static check holds every claim to them.

Cada afirmación del SDD tiene un notebook de nivel 4 en cada idioma que la demuestra; el índice de cada árbol lista las afirmaciones
con sus notebooks ([en/README.md](en/README.md), [es/README.md](es/README.md)), y la comprobación estática sostiene cada afirmación
con ellos.

