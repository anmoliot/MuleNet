# Data Sources and Consent

No raw/generated/processed datasets are committed. The new loaders never fall
back to a simulator. Missing files, invalid rows, currencies, labels and timestamps
raise errors. Dataset bytes and supplier metadata are hashed in download receipts
under reports/. No authorized benchmark files were available for this execution;
the user will provide them later. No benchmark/model performance is reported.

## IBM AMLworld

Primary laundering-typology benchmark: HI-Small and LI-Small transaction CSVs from
[the supplier's Kaggle listing](https://www.kaggle.com/datasets/ealtman2019/ibm-transactions-for-anti-money-laundering-aml).
[IBM's source description](https://github.com/IBM/AML-Data/blob/main/README.md)
identifies the data as simulated and distinguishes its CDLA-Sharing-1.0 data
license from the repository's Apache code license. Review the actual supplier
terms before use or redistribution; this is a provenance note, not legal advice.

```text
python scripts/download_data.py --dataset amlworld --variant HI-Small --license-acknowledged CDLA-Sharing-1.0
python scripts/download_data.py --dataset amlworld --variant LI-Small --license-acknowledged CDLA-Sharing-1.0
```

Authenticate the official Kaggle CLI locally. No tokens go in commands, reports,
chat or the repository. The downloader refuses missing credentials, metadata and
empty output, stages incomplete downloads, and never overwrites an existing CSV.
Actual authenticated download remains untested until credentials are supplied.
CLI syntax follows [Kaggle's documentation](https://github.com/Kaggle/kaggle-cli/blob/main/docs/datasets.md).

Loader semantics: preserve every transaction with its timestamp and row ID;
namespace account IDs by bank; duplicate Account headers are read positionally.
Use Payment Currency as the amount numeraire. Extract features per currency, never
sum USD/EUR/INR. Receiver figures represent paid-denomination flow, not a verified
FX conversion or settled received balance. Aggregate laundering flags support
future-window account labels; optional pattern files are not inferred from fraud
flags and external per-typology evaluation needs supplier pattern annotations.

## PaySim

Secondary transaction benchmark only, from
[the author's linked dataset](https://www.kaggle.com/datasets/ealaxi/paysim1).
The [simulator author](https://github.com/EdgarLopezPhD/PaySim) describes simulated
mobile-money data. Do not call it real bank ground truth. The simulator's GPL
license is not automatically the dataset license. The rendered Kaggle page did
not expose readable license metadata during this execution; verify the current
dataset terms there and pass the license ID you actually accept to the downloader:

```text
python scripts/download_data.py --dataset paysim --variant default --license-acknowledged LICENSE_ID_FROM_SUPPLIER
```

No claim that dataset licensing has been cleared is made. Metadata is retained
locally and hashed. Currency is XXX (unspecified simulated units), not INR. Steps
are treated as event-hour offsets. Balance-delta errors on already observed past
events are available with missingness indicators; never use future transaction
balances to predict their own labels. A later transaction-level diagnostic must
separately disclose any contemporaneous/post-transfer balances. Originator
repetition must be measured from the supplied file; near-unique originators are a
known dataset limitation, NOT a measured statistic in this checkout. PaySim alone
cannot validate generalization to multi-hop laundering topology.

## Own Simulator

```text
cd ml_service
python -m simulation.generator --allow-synthetic --out ../data/generated/demo.json
```

Synthetic consent is mandatory, JSON is stamped data_provenance:
synthetic, and no automatic fallback is supported. Configuration controls graph
components, days, typologies, layering depth, relay delay, splitting, merchant hop,
timing/amount noise and fraud probability. Benign cycles, pass-through merchants,
salary/rent/EMI and noise overlap suspicious patterns. IDs do not encode labels.
Typology/account tags are annotations, never feature inputs. This is a structural
stress fixture, not a validated ledger simulator or evidence of economic benefit.

New core events use UTC epoch seconds. Window bounds are left-open/right-closed;
feature edges satisfy ts <= as_of; labels use (as_of, as_of + horizon] with an
explicit completeness watermark. Event arrival is assumed immediately observable:
backdated investigator labels require a separate known-at-time history before
production use. Duplicate IDs are idempotent; conflicting payloads are rejected.
