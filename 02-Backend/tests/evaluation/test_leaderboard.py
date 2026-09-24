from evaluation.leaderboard import Leaderboard, LeaderboardEntry


def test_leaderboard_submit_and_rank():
    lb = Leaderboard(name="lb")
    lb.submit("a", 10.0)
    lb.submit("b", 20.0)
    lb.submit("c", 15.0)
    ranking = lb.ranking()
    assert ranking[0].name == "b"
    assert ranking[0].rank == 1
    assert ranking[1].name == "c"
    assert ranking[2].name == "a"


def test_leaderboard_top():
    lb = Leaderboard(name="lb")
    for i in range(15):
        lb.submit(f"p{i}", float(i))
    top = lb.top(n=5)
    assert len(top) == 5
    assert top[0].score == 14.0


def test_leaderboard_max_size():
    lb = Leaderboard(name="lb", max_size=3)
    lb.submit("a", 1.0)
    lb.submit("b", 2.0)
    lb.submit("c", 3.0)
    lb.submit("d", 4.0)
    assert lb.size() == 3
    assert lb.get("a") is None


def test_leaderboard_no_downgrade():
    lb = Leaderboard(name="lb")
    entry1 = lb.submit("a", 10.0)
    entry2 = lb.submit("a", 5.0)
    assert entry1 is entry2
    assert lb.get("a").score == 10.0


def test_leaderboard_get():
    lb = Leaderboard(name="lb")
    lb.submit("x", 100.0)
    assert lb.get("x").score == 100.0
    assert lb.get("y") is None
