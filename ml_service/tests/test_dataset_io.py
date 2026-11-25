import hashlib

import pytest

from mulenet_core.io import load_amlworld, load_paysim, read_dataset, write_dataset
from simulation.generator import TYPOLOGIES, SimulationConfig, generate


def test_generator_reproducibility_typologies_and_adversarial_knobs(tmp_path):
    one, two = tmp_path / "one.json", tmp_path / "two.json"
    config = SimulationConfig()
    first = generate(config)
    assert write_dataset(first, one) == write_dataset(generate(config), two)
    assert one.read_bytes() == two.read_bytes()
    assert hashlib.sha256(one.read_bytes()).hexdigest() == hashlib.sha256(two.read_bytes()).hexdigest()
    assert set(TYPOLOGIES) <= {e.typology for e in first.transactions if e.fraud}
    assert any(e.typology == "legit_cycle" and not e.fraud for e in first.transactions)
    assert first.data_provenance == "synthetic"
    with pytest.raises(ValueError, match="allow-synthetic"):
        read_dataset(one)
    assert read_dataset(one, allow_synthetic=True) == first
    changed = generate(SimulationConfig(delay_seconds=7200, split_count=7, merchant_hop=True))
    assert changed != first
    assert len({e.transaction_id for e in first.transactions}) == len(first.transactions)


def test_amlworld_duplicate_headers_banks_times_and_multiedges(tmp_path):
    path = tmp_path / "aml.csv"
    path.write_text("Timestamp,From Bank,Account,To Bank,Account,Amount Paid,Payment Currency,Payment Format,Is Laundering\n2022/09/01 00:00,1,abc,2,abc,10,US Dollar,ACH,0\n2022/09/01 00:01,1,abc,2,abc,20,US Dollar,ACH,1\n", encoding="utf-8")
    data = load_amlworld(path)
    assert len(data) == 2
    assert data[0].source == "1:abc" and data[0].target == "2:abc"
    assert data[1].ts - data[0].ts == 60
    assert data[1].fraud is True and data[0].currency == "USD"
    with pytest.raises(FileNotFoundError):
        load_amlworld(tmp_path / "absent.csv")
    path.write_text("Timestamp,Account\nbad,a\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_amlworld(path)


def test_paysim_balance_fields_and_strict_labels(tmp_path):
    path = tmp_path / "paysim.csv"
    header = "step,type,amount,nameOrig,nameDest,isFraud,oldbalanceOrg,newbalanceOrig,oldbalanceDest,newbalanceDest\n"
    path.write_text(header + "1,TRANSFER,10,a,b,1,20,10,5,15\n", encoding="utf-8")
    data = load_paysim(path)
    assert data[0].ts == 3600 and data[0].currency == "XXX"
    assert data[0].sender_balance_after == 10
    path.write_text(header + "1,TRANSFER,10,a,b,unknown,20,10,5,15\n", encoding="utf-8")
    with pytest.raises(ValueError, match="binary"):
        load_paysim(path)
