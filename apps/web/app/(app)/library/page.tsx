'use client';

import { Card } from '@/components/ui/card';
import { FileText, BookOpen, Code, Image } from 'lucide-react';

const savedItems = [
  { id: '1', title: 'React Best Practices', type: 'document', createdAt: new Date('2026-09-12'), description: 'A comprehensive guide to React development patterns.' },
  { id: '2', title: 'API Documentation', type: 'code', createdAt: new Date('2026-09-10'), description: 'REST API endpoints and authentication guide.' },
  { id: '3', title: 'Project Architecture', type: 'code', createdAt: new Date('2026-09-08'), description: 'System architecture diagrams and data flow.' },
  { id: '4', title: 'Brand Assets', type: 'image', createdAt: new Date('2026-09-05'), description: 'Logos, colors, and brand guidelines.' },
];

const typeIcons: Record<string, React.ElementType> = {
  document: FileText,
  code: Code,
  image: Image,
};

const typeLabels: Record<string, string> = {
  document: 'Document',
  code: 'Code',
  image: 'Image',
};

export default function LibraryPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Library</h1>
        <p className="text-muted-foreground">Access your saved items and resources.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {savedItems.map((item) => {
          const Icon = typeIcons[item.type] || FileText;
          return (
            <Card key={item.id} className="p-6 hover:shadow-md transition-shadow cursor-pointer">
              <div className="flex items-start gap-4">
                <div className="rounded-lg bg-primary/10 p-2">
                  <Icon className="h-6 w-6 text-primary" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-medium truncate">{item.title}</h3>
                  <p className="text-sm text-muted-foreground line-clamp-2">{item.description}</p>
                  <div className="flex items-center gap-2 mt-2">
                    <span className="text-xs text-muted-foreground">{typeLabels[item.type]}</span>
                    <span className="text-xs text-muted-foreground">-</span>
                    <span className="text-xs text-muted-foreground">{item.createdAt.toLocaleDateString()}</span>
                  </div>
                </div>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
