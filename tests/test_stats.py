from server.services.stats_svc import get_system_stats, _gpu_monitor

def test_system_stats_structure():
    stats = get_system_stats()
    assert isinstance(stats, dict)
    assert "cpu" in stats
    assert "ram" in stats
    assert "gpu" in stats
    assert "gpu_name" in stats

    assert isinstance(stats["cpu"], int)
    assert 0 <= stats["cpu"] <= 100

    assert isinstance(stats["ram"], int)
    assert 0 <= stats["ram"] <= 100

    assert isinstance(stats["gpu"], int)
    assert 0 <= stats["gpu"] <= 100

    assert isinstance(stats["gpu_name"], str)
