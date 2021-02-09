# gap2-testcases

Testsuite and driver facilities for testing GAP2 codes. (build time)

## Requirements

- Python >= 3.5 or Python2 >= 2.7.18 to run the driver script.
- WIEN2k for preparing DFT starting point. Favorably version 14.2
- GAP (>=2c) code, for generating inputs for GW and running test.

Note that environment variable `WIENROOT` must be set if one wants
to initialize the WIEN2k and GAP inputs.

## Usage

To use the testsuite, clone the repository to some local path, then enter the path and perform the tests by

```bash
python gap_test.py
```

The input files in `inputs` will be symlinked to `workspace` directory and start the testing of `gap`.
When the test finished, you can use `cp -rL workspace path/to/store` to copy all the results and inputs
to `path/to/store`. Pay attention to large temporary files, e.g. `.eps`, when copying.

## Directory hierarchy

```plain
├── backend
├── init
├── refs
└── struct_files
```

Explanation:

- `backend`: supporting facilities for the driver script `gap_test.py`
- `init`: initialization files of test cases, grouped by target test functionality and/or category of material
- `struct_files`: repository of `.struct` WIEN2k master input files

## Prepare inputs

The cases distributed along with the test infrastructure cannot be run directly after clone,
since the input files for GAP in some testcases can be too large for a compact remote repository.
Therefore users need to generate the WIEN2k and GW inputs themselves.

To do this, please issue the command

```bash
python gap_test.py --init
```

to start a WIEN2k calculation and a following `gap2_init`. Make sure that `run_lapw` is available from the environment.

If you already have the SCF inputs and only need to regenerate the GAP inputs, you can run

```bash
python gap_test.py --init-gap
```

## JSON as control for test cases

This part gives more details about initialization of WIEN2k and GAP inputs as well as running for a test case.
Each test case is defined by a control file named after `dddd_xxxx.json`, where `dddd` is an integer number and `xxxx` is any explaning strings for users. The controls files are stored in subdirectories in  `init`.

### Generator file

A test case for silicon has the following JSON structure

```json
{
  "casename": "Si",
  "task": "gw",
  "is_sp": false,
  "rkmax": 6.0,
  "scf": {
    "version": null,
    "kmesh_scf": [8, 8, 8],
    "vxc": 13,
    "numk": 512,
    "ec": 1.0e-8,
    "ecut": -6.0
  },
  "gap": {
    "version": null,
    "kmesh_gw": [2, 2, 2],
    "nprocs": [64, 32, 16, 8, 4, 2, 1],
    "nkpt": 8,
    "emax": 5.0
  }
}
```

The meaning of each key-value pair is explained below.

#### Required keys

- `casename`: the case name of struct file. Note that the driver will try to find the `struct` file with the same case name in the `struct_files` directory. Make sure that this file exists.
- `task`: category of task for present test.
- `rkmax`: basis set of the augmented plane waves
- `is_sp`: if the initialization is spin-polarized
- `scf`: a dictionary containing the initialization and running parameters for WIEN2k self-consistent field calculation.
- `gap`: a dictionary containing the parameters parsed to `gap_init`.

#### `scf` dictionary

- `version`: required WIEN2k version. `null` for any version.
- `vxc`: an integer number for specification of exchange-correlation functional
- `numk`: number of kpoints
- `kmesh_scf`: intended kmesh for SCF set by `kgen` with `numk`
- `ecut`: cutoff energy between core and valence regimes

and other parameters that `init_lapw` accpets.

#### `gap` dictionary

- `version`: required GAP version. `null` for any version.
- `nkp`: number of kpoints for GW
- `kmesh_gw`: intended kmesh for GW set by `kgen` with `nkp`
- `nprocs`: number of processors appropriate for running the case. It is usually a factor of the number of q(k) points. The driver will detect the largest one smaller than the number of available processors.

and other parameters that `gap_init` accepts.

### Categories of test cases

All test cases are placed in the `init` directory

```plain
init
├── JH16  : GW test cases used in H. Jiang, PRB 93, 115203 (2016)
├── gw_ml : GW test cases of monolayer structures
├── gw_sp : GW test cases of sp semiconductor
├── gw_tm : GW test cases of transition metal compounds
├── hf_ml : Hartree-Fock test cases of monolayer structures
└── hf_sp : Hartree-Fock test cases of sp semiconductor
```


## TODO

- [ ] keys for HLOs inputs. This may involve changing the behavior of `gap2<ver>_init`
- [ ] data analysis and comparison
- [ ] packing and display of results

