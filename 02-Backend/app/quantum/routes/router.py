from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import numpy as np
import time

from app.quantum.circuit_simulator import QuantumCircuitSimulator, simulate_circuit
from app.quantum.qml_algorithms import QuantumMachineLearning
from app.quantum.qnlp import QuantumNLP
from app.quantum.crypto import QuantumCrypto
from app.quantum.qkd import QuantumKeyDistribution
from app.quantum.qrandom import QuantumRandomNumberGenerator
from app.quantum.hybrid_workflows import HybridQuantumWorkflow
from app.quantum.benchmarks import QuantumBenchmark
from app.quantum.vqc import VariationalQuantumCircuit
from app.quantum.qnn import QuantumNeuralNetwork
from app.quantum.qaoa import QAOA
from app.quantum.counting import QuantumApproximateCounting
from app.quantum.amplitude_estimation import QuantumAmplitudeEstimation
from app.quantum.phase_estimation import QuantumPhaseEstimation
from app.quantum.hybrid_optimizer import HybridQuantumOptimizer

router = APIRouter(prefix="/quantum", tags=["quantum"])

class GateModel(BaseModel):
    type: str
    qubits: List[int]
    params: List[float] = []

class CircuitRequest(BaseModel):
    num_qubits: int
    gates: List[GateModel]
    shots: int = 1024

class QMLTrainRequest(BaseModel):
    num_qubits: int
    X: List[List[float]]
    y: List[float]
    epochs: int = 50
    task_type: str = "classification"

class QMLPredictRequest(BaseModel):
    num_qubits: int
    X: List[List[float]]
    weights: Optional[List[float]] = None

class QKDRequest(BaseModel):
    num_bits: int = 256
    protocol: str = "bb84"

class OptimizeRequest(BaseModel):
    bounds: List[List[float]]
    max_iter: int = 50
    method: str = "quantum"

class NLPRequest(BaseModel):
    text: str
    task: str = "similarity"
    compare_text: Optional[str] = None

class QAOASolveRequest(BaseModel):
    num_qubits: int
    edges: List[List[int]]
    weights: Optional[List[float]] = None
    depth: int = 2

@router.post("/circuit/simulate")
async def simulate(request: CircuitRequest):
    try:
        result = simulate_circuit(request.num_qubits, [g.dict() for g in request.gates], request.shots)
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.get("/circuit/gates")
async def list_gates():
    return {"gates": [g.value for g in __import__("app.quantum.circuit_simulator", fromlist=["GateType"]).GateType]}

@router.post("/qml/train")
async def qml_train(request: QMLTrainRequest):
    try:
        qml = QuantumMachineLearning(request.num_qubits)
        X = np.array(request.X)
        y = np.array(request.y)
        start = time.time()
        qml.train(X, y, epochs=request.epochs)
        preds = qml.predict(X)
        accuracy = float(np.mean(preds == y))
        return {"accuracy": accuracy, "training_time": time.time() - start}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.post("/qml/predict")
async def qml_predict(request: QMLPredictRequest):
    try:
        qml = QuantumMachineLearning(request.num_qubits)
        if request.weights:
            qml.weights = np.array(request.weights)
        preds = qml.predict(np.array(request.X)).tolist()
        return {"predictions": preds}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.post("/qnlp/similarity")
async def qnlp_similarity(request: NLPRequest):
    try:
        nlp = QuantumNLP()
        sim = nlp.similarity(request.text, request.compare_text or "")
        return {"similarity": sim}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.post("/qnlp/sentiment")
async def qnlp_sentiment(request: NLPRequest):
    try:
        nlp = QuantumNLP()
        result = nlp.quantum_sentiment(request.text)
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.post("/qkd/generate")
async def qkd_generate(request: QKDRequest):
    try:
        qkd = QuantumKeyDistribution()
        if request.protocol == "bb84":
            result = qkd.bb84(request.num_bits)
        elif request.protocol == "e91":
            result = qkd.e91(request.num_bits)
        else:
            result = qkd.b92(request.num_bits)
        return {"alice_key": result.raw_key, "bob_key": result.sifted_key, "error_rate": result.error_rate, "protocol": result.protocol}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.post("/qkd/secret")
async def qkd_secret():
    try:
        qkd = QuantumKeyDistribution()
        secret, raw = qkd.generate_shared_secret()
        return {"secret": secret, "raw_key": raw}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.get("/qrandom/generate")
async def qrandom_generate(num_bytes: int = 32):
    try:
        qrng = QuantumRandomNumberGenerator()
        result = qrng.generate()
        return {"random_bytes": result.random_bytes[:num_bytes].hex(), "entropy": result.entropy}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.get("/qrandom/int")
async def qrandom_int(min_val: int = 0, max_val: int = 100):
    try:
        qrng = QuantumRandomNumberGenerator()
        val = qrng.generate_int(min_val, max_val)
        return {"value": val}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.get("/qrandom/password")
async def qrandom_password(length: int = 16):
    try:
        qrng = QuantumRandomNumberGenerator()
        pwd = qrng.generate_password(length)
        return {"password": pwd}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.post("/optimize")
async def optimize(request: OptimizeRequest):
    try:
        def objective(x):
            return sum(x ** 2)
        optimizer = HybridQuantumOptimizer()
        result = optimizer.optimize(objective, [tuple(b) for b in request.bounds], method=request.method, max_iter=request.max_iter)
        return {"best_x": result.best_x.tolist(), "best_f": result.best_f, "method": result.method}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.post("/qaoa/solve")
async def qaoa_solve(request: QAOASolveRequest):
    try:
        qaoa = QAOA(request.num_qubits)
        edges = [tuple(e) for e in request.edges]
        result = qaoa.maxcut(edges, weights=request.weights, depth=request.depth)
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.post("/benchmark/grover")
async def benchmark_grover(num_qubits: int = 4, target: int = 0):
    try:
        bench = QuantumBenchmark()
        result = bench.benchmark_grover(target, num_qubits)
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.post("/benchmark/all")
async def benchmark_all():
    try:
        np.random.seed(42)
        X = np.random.randn(20, 4)
        y = (X[:, 0] + X[:, 1] > 0).astype(int)
        bench = QuantumBenchmark()
        results = bench.run_all(X, y)
        return bench.summary()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@router.get("/benchmark/summary")
async def benchmark_summary():
    bench = QuantumBenchmark()
    return bench.summary()
