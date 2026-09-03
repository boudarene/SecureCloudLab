from pathlib import Path


def test_expected_project_files_exist():
    root = Path(__file__).resolve().parents[1]
    expected = [
        "docker-compose.yml",
        "app/Dockerfile",
        "app/main.py",
        "nginx/nginx.conf",
        "prometheus/prometheus.yml",
    ]
    for relative in expected:
        assert (root / relative).exists(), relative
