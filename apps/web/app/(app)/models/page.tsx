'use client';

import { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Check, Sparkles } from 'lucide-react';

const MODELS = [
  {
    id: 'gpt-4',
    name: 'GPT-4',
    description: 'Best for complex reasoning and creative tasks.',
    provider: 'OpenAI',
    contextWindow: '8K',
    badge: 'Popular',
  },
  {
    id: 'gpt-4o',
    name: 'GPT-4o',
    description: 'Optimized omni model with faster responses.',
    provider: 'OpenAI',
    contextWindow: '128K',
    badge: 'Recommended',
  },
  {
    id: 'claude-3.5-sonnet',
    name: 'Claude 3.5 Sonnet',
    description: 'Strong instruction following and coding ability.',
    provider: 'Anthropic',
    contextWindow: '200K',
    badge: null,
  },
  {
    id: 'gemini-1.5-pro',
    name: 'Gemini 1.5 Pro',
    description: 'Deep multimodal context for long documents.',
    provider: 'Google',
    contextWindow: '1M',
    badge: null,
  },
  {
    id: 'llama-3.1-70b',
    name: 'Llama 3.1 70B',
    description: 'Open-weight alternative for self-host setups.',
    provider: 'Meta',
    contextWindow: '128K',
    badge: 'Open',
  },
];

export default function ModelsPage() {
  const [selectedId, setSelectedId] = useState('gpt-4o');

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Models</h1>
        <p className="text-muted-foreground">
          Choose the primary model and inspect available options.
        </p>
      </div>

      <Card className="p-5">
        <div className="flex items-center gap-3 mb-4">
          <Sparkles className="h-5 w-5 text-primary" />
          <div>
            <p className="text-sm font-medium">Active Model</p>
            <p className="text-xs text-muted-foreground">
              Used for new conversations and chat completions.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" className="flex-1">
            Change Model
          </Button>
          <Button variant="secondary" className="flex-1">
            Configure Default
          </Button>
        </div>
      </Card>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {MODELS.map((model) => {
          const isSelected = model.id === selectedId;
          return (
            <Card
              key={model.id}
              className={`p-5 transition-shadow hover:shadow-md ${
                isSelected ? 'ring-2 ring-primary' : ''
              }`}
            >
              <div className="flex items-center justify-between mb-3">
                <div>
                  <h2 className="font-semibold text-sm">{model.name}</h2>
                  <p className="text-xs text-muted-foreground">{model.provider}</p>
                </div>
                <div className="flex items-center gap-2">
                  {model.badge && (
                    <Badge variant="outline" className="text-[10px]">
                      {model.badge}
                    </Badge>
                  )}
                  {isSelected && (
                    <Badge variant="default" className="text-[10px]">
                      <Check className="mr-1 h-3 w-3" />
                      Active
                    </Badge>
                  )}
                </div>
              </div>

              <p className="text-xs text-muted-foreground mb-4 line-clamp-2">
                {model.description}
              </p>

              <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                <span>Context: {model.contextWindow}</span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 px-2 text-[10px]"
                  onClick={() => setSelectedId(model.id)}
                >
                  {isSelected ? 'Selected' : 'Select'}
                </Button>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
