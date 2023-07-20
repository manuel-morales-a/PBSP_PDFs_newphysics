# Running contaminated fits

## Preparing data and theory predictions
Before launching a contaminated fit, you will need to ensure that the C-factors, FK-tables, commondata, systype and plotting files are all in the correct place. This can be achieved using:

```
cp -r files_for_commondata/* /path/to/miniconda3/envs/contamination-dev/share/NNPDF/data/commondata/.
cp -r files_for_theory/* /path/to/miniconda3/envs/contamination-dev/share/NNPDF/data/theory_num/.
```

where theory_num is the appropriate theory you would like to work with (e.g. theory_53, theory_200). You will also need to copy and paste the filters.yaml file to the correct location, via:

```
cp filters.yaml /path/to/nnpdf/installation/nnpdf/validphys2/src/validphys/cuts/.
```

## Launching contaminated fits
The code for launching contaminated fits is contained in the fitting_code folder. Running the code follows the standard NNPDF pipeline, with a small modification in the first step.

Instead of running vp-setupfit on a runcard first, you should run:

```
validphys example_contamination.yaml -x contamination_provider.py
```

The example_contamination.yaml file is the basic runcard for the contaminated fit, together with some additional namespaces. Executing the above command will do the following:

- Create new SMEFT C-factor files in the correct directory, scaled to the required user-specified values.
- Write a new runcard with the C-factor names changed to appropriate scaled names, allowing the scaled values to be used.
- Launch vp-setupfit.
- Launch vp-rebuild-data to build the correct commondata.
- Remove the runcard containing the SMEFT C-factors, and replace it with a SM runcard.

After this, the pipeline is identical to a normal NNPDF fit. Run n3fit, evolven3fit and postfit as usual.

## Analysing contaminated fits
The code for analysing contaminated fits is contained in the analysis_code folder. Run the code via the command:

```
validphys example_analysis.yaml -x analysis_provider.py
```

The example_analysis.yaml file contains all the information needed for the analysis. A validphys report will be produced from the analysis which can be uploaded to the server and shared.