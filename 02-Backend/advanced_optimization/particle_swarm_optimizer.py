import copy
import random


def particle_swarm_optimization(f, bounds, n_particles=30, max_iter=100, w=0.7, c1=1.5, c2=1.5):
    dim = len(bounds)
    particles = [[random.uniform(b[0], b[1]) for b in bounds] for _ in range(n_particles)]
    velocities = [[random.uniform(-1, 1) for _ in range(dim)] for _ in range(n_particles)]

    pbest = [list(p) for p in particles]
    pbest_fitness = [f(p) for p in particles]
    gbest_idx = min(range(n_particles), key=lambda i: pbest_fitness[i])
    gbest = list(pbest[gbest_idx])

    for _ in range(max_iter):
        for i in range(n_particles):
            for j in range(dim):
                r1 = random.random()
                r2 = random.random()
                velocities[i][j] = (
                    w * velocities[i][j]
                    + c1 * r1 * (pbest[i][j] - particles[i][j])
                    + c2 * r2 * (gbest[j] - particles[i][j])
                )
                particles[i][j] += velocities[i][j]
                particles[i][j] = max(bounds[j][0], min(bounds[j][1], particles[i][j]))

            fitness = f(particles[i])
            if fitness < pbest_fitness[i]:
                pbest[i] = list(particles[i])
                pbest_fitness[i] = fitness
                if fitness < pbest_fitness[gbest_idx]:
                    gbest_idx = i
                    gbest = list(particles[i])

    return gbest
