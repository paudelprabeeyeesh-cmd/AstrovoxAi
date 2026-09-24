from lifelong_learning.task_inventory import Task, TaskInventory


class TestTaskInventory:
    def test_register_task(self):
        inv = TaskInventory()
        task = inv.register("t1", "Train model")
        assert task.task_id == "t1"
        assert task.name == "Train model"
        assert task.status == "pending"

    def test_register_duplicate_raises(self):
        inv = TaskInventory()
        inv.register("t1", "Task 1")
        with ValueError:
            inv.register("t1", "Task 1 again")

    def test_update_status(self):
        inv = TaskInventory()
        inv.register("t1", "Task 1")
        task = inv.update_status("t1", "running")
        assert task.status == "running"
        assert inv.get_task("t1").status == "running"

    def test_update_unknown_raises(self):
        inv = TaskInventory()
        with KeyError:
            inv.update_status("unknown", "done")

    def test_list_tasks(self):
        inv = TaskInventory()
        inv.register("t1", "A", metadata={}, status="pending")
        inv.register("t2", "B", metadata={}, status="done")
        inv.register("t3", "C", metadata={}, status="done")
        all_tasks = inv.list_tasks()
        assert len(all_tasks) == 3
        done_tasks = inv.list_tasks(status="done")
        assert len(done_tasks) == 2

    def test_get_summary(self):
        inv = TaskInventory()
        inv.register("t1", "A")
        inv.register("t2", "B")
        inv.update_status("t1", "running")
        summary = inv.get_summary()
        assert summary["total_tasks"] == 2
        assert summary["status_counts"]["pending"] == 1
        assert summary["status_counts"]["running"] == 1

    def test_remove_task(self):
        inv = TaskInventory()
        inv.register("t1", "Task 1")
        inv.remove("t1")
        assert inv.get_task("t1") is None

    def test_remove_unknown_raises(self):
        inv = TaskInventory()
        with KeyError:
            inv.remove("unknown")
