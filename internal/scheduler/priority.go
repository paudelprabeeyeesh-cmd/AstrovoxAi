package scheduler

import "container/heap"

// PriorityQueue is a min-heap of tasks by priority (lower = higher priority).
type PriorityQueue struct {
	items []*priorityItem
}

type priorityItem struct {
	task    *Task
	priority int
	index   int
}

func (pq PriorityQueue) Len() int { return len(pq.items) }
func (pq PriorityQueue) Less(i, j int) bool {
	return pq.items[i].priority < pq.items[j].priority
}
func (pq PriorityQueue) Swap(i, j int) {
	pq.items[i], pq.items[j] = pq.items[j], pq.items[i]
	pq.items[i].index = i
	pq.items[j].index = j
}

func (pq *PriorityQueue) Push(x interface{}) {
	item := x.(*priorityItem)
	item.index = len(pq.items)
	pq.items = append(pq.items, item)
}

func (pq *PriorityQueue) Pop() interface{} {
	old := pq.items
	n := len(old)
	item := old[n-1]
	item.index = -1
	pq.items = old[:n-1]
	return item
}

// PushTask adds a task with a priority.
func (pq *PriorityQueue) PushTask(task *Task, priority int) {
	heap.Push(pq, &priorityItem{task: task, priority: priority})
}

// PopTask removes and returns the highest-priority task.
func (pq *PriorityQueue) PopTask() *Task {
	if pq.Len() == 0 {
		return nil
	}
	item := heap.Pop(pq).(*priorityItem)
	return item.task
}
