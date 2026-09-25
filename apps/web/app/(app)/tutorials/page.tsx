'use client';

import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Loader2, Play, BookOpen, Clock, BarChart3 } from 'lucide-react';
import { api } from '@/lib/api';
import { Tutorial } from '@/lib/api';
import Link from 'next/link';

const DIFFICULTIES = ['beginner', 'intermediate', 'advanced'];

export default function TutorialsPage() {
  const [tutorials, setTutorials] = useState<Tutorial[]>([]);
  const [loading, setLoading] = useState(true);
  const [difficulty, setDifficulty] = useState<string | null>(null);

  useEffect(() => {
    loadTutorials();
  }, [difficulty]);

  const loadTutorials = async () => {
    setLoading(true);
    try {
      const data = await api.get<{ tutorials: Tutorial[] }>(`/support/tutorials${difficulty ? `?difficulty=${difficulty}` : ''}`);
      setTutorials(data.tutorials || []);
    } catch {
      setTutorials([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Tutorials</h1>
        <p className="text-muted-foreground">Step-by-step guides to help you master AstrovoxAi.</p>
      </div>

      <div className="flex gap-2">
        <Badge
          variant={difficulty === null ? 'default' : 'secondary'}
          className="cursor-pointer"
          onClick={() => setDifficulty(null)}
        >
          All Levels
        </Badge>
        {DIFFICULTIES.map((d) => (
          <Badge
            key={d}
            variant={difficulty === d ? 'default' : 'secondary'}
            className="cursor-pointer capitalize"
            onClick={() => setDifficulty(d)}
          >
            {d}
          </Badge>
        ))}
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : tutorials.length === 0 ? (
        <Card className="p-12 text-center">
          <BookOpen className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="text-lg font-medium">No tutorials found</h3>
          <p className="text-muted-foreground">Check back later for new tutorials.</p>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {tutorials.map((tutorial) => (
            <Card key={tutorial.id} className="p-4 hover:shadow-md transition-shadow">
              <Link href={`/tutorials/${tutorial.id}`}>
                <div className="flex items-start justify-between gap-2">
                  <h3 className="font-semibold text-sm">{tutorial.title}</h3>
                  <Badge variant="secondary" className="text-xs capitalize">{tutorial.difficulty}</Badge>
                </div>
                <p className="mt-2 text-sm text-muted-foreground line-clamp-2">{tutorial.description}</p>
                <div className="mt-3 flex items-center gap-4 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <BookOpen className="h-3 w-3" /> {tutorial.steps.length} steps
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" /> {tutorial.estimated_time} min
                  </span>
                </div>
              </Link>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
