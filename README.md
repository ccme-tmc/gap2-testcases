# gap2-testcases

Testsuite for testing GAP2 codes.

## Requirements

- Python >= 3.5 or Python2 >= 2.7.18 to run generator script.
- Wien2k for preparing DFT starting point. Favorably version 14.2
- GAP code, for generating inputs for GW and test.

## Usage

To use the testsuite, clone the repository to some local path, then enter the path and perform the tests by

```bash
python gap_test.py
```

However, the cases distributed along with the test infrastructure is not a complete set,
since the input files for GAP can be too large for convenient distribution.
In this case, for users a complete test who wants  to generate the GW inputs themselves, fire

```bash
python gap_test.py --init
```

before running the tests.

## Build WIEN2k and GAP inputs

This part gives more details about initialization of WIEN2k and GAP inputs.
The control file is named after `xxx.json`, where `xxx` is an integer number.
For example, a test case for face-centered cubic TiC has the following JSON structure

```json
{
  "casename": "TiC",
  "suffix": "normalgw",
  "sp": false,
  "rkmax": 6.0,
  "w2k": {
    "kmesh_scf": [8, 8, 8],
    "numk": 512,
    "ecut": -6.0
  },
  "gap": {
    "vxc": 13,
    "kmesh_gw": [2, 2, 2],
    "nkptgw": 8
  }
}
```

