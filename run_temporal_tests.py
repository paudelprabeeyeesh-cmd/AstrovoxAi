import sys, datetime, time as time_mod
sys.path.insert(0, '.')

from app.temporal import (
    BreakpointType, ConsistencyLevel, ConsistencyManager,
    ConversationTimeline, CausalChainAnalyzer, CausalLink,
    DecisionTree, Direction, GSet, HistoricalPatternRecognizer,
    ImmutableStateTree, LWWRegister, ORSet, PNCounter,
    ScenarioAnalyzer, StateDiffer, StatePredictor, StateSnapshot,
    TemporalAttention, TemporalBreakpoint, TemporalDatabase,
    TimeAwareContextWindow, TimeSeriesForecaster, TimeTravelDebugger,
    TimelineExporter, TimelineNode, get_debugger
)

failures = []
passes = 0

def run_test(name, fn):
    global passes
    try:
        fn()
        passes += 1
        print(f'  PASS: {name}')
    except Exception as e:
        failures.append(f'{name}: {e}')
        print(f'  FAIL: {name} - {e}')

# TestTimeTravelDebugger
print('TestTimeTravelDebugger')
def test_capture_restore():
    d = get_debugger('test1')
    state = {'step': 1, 'value': 42}
    snap = d.capture_snapshot(state, label='init')
    assert snap.state == state
    restored = d.restore_snapshot(snap.snapshot_id)
    assert restored['step'] == 1
run_test('capture_and_restore', test_capture_restore)

def test_branch_switch():
    d = get_debugger('test2')
    branch_id = d.create_branch('experiment', created_by='test')
    branches = d.list_branches()
    assert any(b['branch_id'] == branch_id for b in branches)
    d.switch_branch(branch_id)
    assert d.get_current_branch() == branch_id
run_test('branch_creation_and_switch', test_branch_switch)

def test_breakpoint():
    d = get_debugger('test3')
    bp = TemporalBreakpoint(breakpoint_id='bp-1', breakpoint_type=BreakpointType.POSITION, target=10, description='stop at 10')
    d.set_breakpoint(bp)
    bps = d.list_breakpoints()
    assert len(bps) == 1
    assert bps[0]['breakpoint_id'] == 'bp-1'
    d.remove_breakpoint('bp-1')
    assert len(d.list_breakpoints()) == 0
run_test('breakpoint_lifecycle', test_breakpoint)

def test_step():
    d = get_debugger('test4')
    d.capture_snapshot({'x': 0}, label='start')
    evt = type('E', (), {'event_id': 'e1', 'timestamp': datetime.datetime.now(datetime.timezone.utc), 'position': 1, 'event_type': 'tick', 'payload': {}, 'branch_id': 'main'})()
    state = d.step_forward(evt, lambda s, e: {'x': s.get('x', 0) + 1})
    assert state['x'] == 1
    d.step_backward(1)
    assert d.get_current_position() == 0
run_test('step_forward_and_backward', test_step)

# TestTemporalDatabase
print('TestTemporalDatabase')
def test_apply_query():
    db = TemporalDatabase(consistency=ConsistencyLevel.EVENTUAL)
    entity = db.apply('e1', 'create', {'name': 'test'}, actor='u1')
    assert entity.version == 1
    state = db.query('e1')
    assert state['name'] == 'test'
run_test('apply_and_query', test_apply_query)

def test_pit_db():
    db = TemporalDatabase(consistency=ConsistencyLevel.EVENTUAL)
    db.apply('e1', 'create', {'v': 1}, actor='u1')
    t = datetime.datetime.now(datetime.timezone.utc)
    time_mod.sleep(0.01)
    db.apply('e1', 'update', {'v': 2}, actor='u1')
    state = db.query('e1', as_of=t)
    assert state['v'] == 1
run_test('point_in_time', test_pit_db)

def test_history_db():
    db = TemporalDatabase(consistency=ConsistencyLevel.EVENTUAL)
    db.apply('e1', 'create', {'v': 1}, actor='u1')
    db.apply('e1', 'update', {'v': 2}, actor='u1')
    history = db.history('e1')
    assert len(history) == 2
run_test('history', test_history_db)

def test_audit():
    db = TemporalDatabase(consistency=ConsistencyLevel.EVENTUAL)
    db.apply('e1', 'create', {'v': 1}, actor='u1')
    trail = db.audit_trail('e1')
    assert len(trail) >= 1
    assert trail[0]['operation'] == 'create'
run_test('audit_trail', test_audit)

def test_lineage():
    db = TemporalDatabase(consistency=ConsistencyLevel.EVENTUAL)
    db.apply('e1', 'create', {'v': 1}, actor='u1')
    lineage = db.lineage('e1')
    assert len(lineage) >= 1
run_test('lineage', test_lineage)

def test_verify():
    db = TemporalDatabase(consistency=ConsistencyLevel.EVENTUAL)
    db.apply('e1', 'create', {'v': 1}, actor='u1')
    assert db.verify_audit_integrity() is True
run_test('verify_audit_integrity', test_verify)

def test_constraint():
    db = TemporalDatabase(consistency=ConsistencyLevel.EVENTUAL)
    db._constraints.register(
        type('C', (), {'constraint_id': 'c1', 'entity_type': 'entity', 'rule': 'x>0', 'validator': lambda ns, _: ns.get('x', 0) > 0, 'enabled': True, 'description': ''})()
    )
    try:
        db.apply('e1', 'create', {'x': -1}, actor='u1', entity_type='entity')
        raise AssertionError('Expected ValueError')
    except ValueError:
        pass
run_test('constraint_violation', test_constraint)

# TestTimeline
print('TestTimeline')
def test_add_msg():
    timeline = ConversationTimeline('conv-1')
    node = timeline.add_message('user', 'hello')
    assert node.content['role'] == 'user'
run_test('add_message', test_add_msg)

def test_branch_merge():
    timeline = ConversationTimeline('conv-2')
    node = timeline.add_message('user', 'hello')
    branch = timeline.branch('alt', node.node_id)
    timeline.add_message('assistant', 'hi', branch_id=branch)
    merged = timeline.merge(branch, 'main', node.node_id)
    assert merged.node_type == 'merge'
run_test('branch_and_merge', test_branch_merge)

def test_divergence():
    timeline = ConversationTimeline('conv-3')
    n1 = timeline.add_message('user', 'hello')
    branch = timeline.branch('alt', n1.node_id)
    timeline.add_message('assistant', 'hi', branch_id=branch)
    divergence = timeline.detect_divergence('main', branch)
    assert divergence is None or isinstance(divergence, str)
run_test('divergence_detection', test_divergence)

def test_visualize():
    timeline = ConversationTimeline('conv-4')
    timeline.add_message('user', 'hello')
    viz = timeline.visualize()
    assert 'nodes' in viz
    assert len(viz['nodes']) >= 1
run_test('visualize', test_visualize)

def test_path():
    timeline = ConversationTimeline('conv-5')
    node = timeline.add_message('user', 'hello')
    path = timeline.get_path_to_root(node.node_id)
    assert len(path) >= 1
run_test('path_to_root', test_path)

def test_decision_tree():
    tree = DecisionTree('tree-1')
    root = tree.add_decision(None, {'question': 'go?'})
    outcome = tree.add_outcome(root.node_id, {'result': 'yes'})
    viz = tree.visualize()
    assert viz['node_count'] >= 2
run_test('decision_tree', test_decision_tree)

def test_scenario():
    timeline = ConversationTimeline('conv-6')
    analyzer = ScenarioAnalyzer(timeline)
    result = analyzer.simulate('s1', 'main', lambda nodes: {'score': 0.5})
    assert result.scenario_id == 's1'
run_test('scenario_analysis', test_scenario)

def test_causal():
    timeline = ConversationTimeline('conv-7')
    n1 = timeline.add_message('user', 'hello')
    n2 = timeline.add_message('assistant', 'hi')
    analyzer = CausalChainAnalyzer(timeline)
    analyzer.add_link(n1.node_id, n2.node_id, 'causes')
    chain = analyzer.analyze(n1.node_id)
    assert chain['start_node_id'] == n1.node_id
run_test('causal_chain', test_causal)

def test_export_json():
    timeline = ConversationTimeline('conv-8')
    timeline.add_message('user', 'hello')
    exporter = TimelineExporter(timeline)
    json_data = exporter.to_json()
    assert 'hello' in json_data
run_test('export_json', test_export_json)

def test_export_csv():
    timeline = ConversationTimeline('conv-9')
    timeline.add_message('user', 'hello')
    exporter = TimelineExporter(timeline)
    csv_data = exporter.to_csv()
    assert 'hello' in csv_data
run_test('export_csv', test_export_csv)

# TestStateManager
print('TestStateManager')
def test_commit_get():
    tree = ImmutableStateTree()
    state = tree.commit('default', {'x': 1})
    assert tree.get('default')['x'] == 1
run_test('commit_and_get', test_commit_get)

def test_history_state():
    tree = ImmutableStateTree()
    tree.commit('default', {'x': 1})
    tree.commit('default', {'x': 2})
    hist = tree.history('default')
    assert len(hist) == 2
run_test('history', test_history_state)

def test_rollback():
    tree = ImmutableStateTree()
    tree.commit('default', {'x': 1})
    tree.commit('default', {'x': 2})
    tree.rollback('default', steps=1)
    assert tree.get('default')['x'] == 1
run_test('rollback', test_rollback)

def test_diff_state():
    tree = ImmutableStateTree()
    tree.commit('default', {'x': 1})
    id_a = tree._latest['default']
    tree.commit('default', {'x': 2})
    id_b = tree._latest['default']
    diff = tree.diff('default', id_a, id_b)
    assert diff['summary']['changed_count'] == 1
run_test('diff', test_diff_state)

def test_optimize():
    tree = ImmutableStateTree()
    tree.commit('default', {'x': 1})
    result = tree.optimize('default')
    assert result['optimized'] is True
run_test('optimize', test_optimize)

def test_state_differ():
    diff = StateDiffer.diff({'a': 1}, {'a': 2, 'b': 3})
    assert diff['summary']['changed_count'] == 1
    assert diff['summary']['added_count'] == 1
run_test('state_differ', test_state_differ)

def test_predictor():
    pred = StatePredictor()
    pred.observe({'a': 1}, {'a': 2}, 1.0)
    predictions = pred.predict({'a': 1}, steps=1)
    assert len(predictions) == 1
run_test('state_predictor', test_predictor)

def test_gset():
    gset = GSet()
    gset.add('a')
    gset.add('b')
    assert gset.has('a')
    assert not gset.has('c')
run_test('crdt_gset', test_gset)

def test_pncounter():
    counter = PNCounter()
    counter.increment()
    counter.decrement()
    assert counter.value() == 0
run_test('crdt_pncounter', test_pncounter)

def test_lww():
    reg = LWWRegister('n1')
    reg.set('hello')
    assert reg.get() == 'hello'
run_test('crdt_lww', test_lww)

def test_orset():
    orset = ORSet()
    orset.add('a')
    assert orset.has('a')
    orset.remove('a')
    assert not orset.has('a')
run_test('crdt_orset', test_orset)

def test_consistency():
    mgr = ConsistencyManager(consistency_level='eventual')
    mgr.propose({'k': 'v'})
    assert len(mgr.get_pending()) == 0
run_test('consistency_manager', test_consistency)

# TestTemporalAI
print('TestTemporalAI')
def test_context():
    cw = TimeAwareContextWindow(max_tokens=10, decay_half_life_s=3600.0)
    cw.add('hello')
    cw.add('world')
    text = cw.context_text()
    assert 'hello' in text
run_test('context_window', test_context)

def test_attention():
    attn = TemporalAttention()
    query = {'timestamp': datetime.datetime.now(datetime.timezone.utc), 'text': 'q'}
    keys = [{'text': 'a'}, {'text': 'b'}]
    ts = [datetime.datetime.now(datetime.timezone.utc), datetime.datetime.now(datetime.timezone.utc)]
    results = attn.attend(query, keys, ts)
    assert len(results) == 2
run_test('temporal_attention', test_attention)

def test_pattern():
    pr = HistoricalPatternRecognizer()
    pr.observe(['a', 'b', 'c'])
    pr.observe(['a', 'b', 'c'])
    patterns = pr.detect_patterns()
    assert len(patterns) >= 1
run_test('pattern_recognizer', test_pattern)

def test_forecast():
    f = TimeSeriesForecaster()
    now = datetime.datetime.now(datetime.timezone.utc)
    f.observe('s1', now, 1.0)
    f.observe('s1', datetime.datetime.fromtimestamp(now.timestamp() + 60, tz=datetime.timezone.utc), 2.0)
    forecast = f.forecast('s1', horizon=2)
    assert len(forecast) == 2
run_test('time_series_forecaster', test_forecast)

# Test API routes
print('Test API Routes')
def test_api_patterns():
    from app.api.routers.temporal_route import _pattern_recognizer
    _pattern_recognizer.observe(['a', 'b'])
    _pattern_recognizer.observe(['a', 'b'])
    patterns = _pattern_recognizer.detect_patterns()
    assert len(patterns) >= 1
run_test('api_patterns_accumulate', test_api_patterns)

print(f'\nResults: {passes} passed, {len(failures)} failed')
for f in failures:
    print(f'  FAIL: {f}')
if not failures:
    print('All tests passed!')
