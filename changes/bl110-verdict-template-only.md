- Release verdict: a part of a gate that skips because the test runs only in the template repository (the template's own
  sources, a second instantiation) reads `not applicable` in the product, with its reason, and the row is judged on its other
  parts; in the template the same skip stays a skip, and it never hides a failed part (CV-014, BL-110). The repository rows
  RP-022, RP-025, RP-026 and RP-029 can now converge in a product.
