import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { Loader2, Search, X, BookOpen, MessageSquare, HelpCircle } from 'lucide-react';
import { api } from '@/lib/api';
import { HelpArticle } from '@/lib/api';
import { useRouter } from 'next/navigation';

export function HelpWidget() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<HelpArticle[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open) return;
    const timer = setTimeout(async () => {
      if (query.length < 2) {
        setResults([]);
        return;
      }
      setLoading(true);
      try {
        const data = await api.searchHelpArticles(query);
        setResults(data.articles || []);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [query, open]);

  const router = useRouter();

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        className="fixed bottom-4 right-4 z-50 shadow-lg"
        onClick={() => setOpen(!open)}
      >
        <HelpCircle className="h-4 w-4 mr-2" />Help
      </Button>

      {open && (
        <Card className="fixed bottom-16 right-4 z-50 w-96 max-h-[500px] shadow-xl flex flex-col">
          <div className="flex items-center justify-between p-3 border-b">
            <span className="font-semibold text-sm">Help Center</span>
            <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => setOpen(false)}>
              <X className="h-4 w-4" />
            </Button>
          </div>
          <div className="p-3">
            <div className="relative">
              <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search help..."
                className="pl-8"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>
          </div>
          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            {loading && (
              <div className="flex justify-center py-4">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
              </div>
            )}
            {!loading && results.length === 0 && query.length >= 2 && (
              <p className="text-sm text-muted-foreground text-center py-4">No results found</p>
            )}
            {results.map((article) => (
              <button
                key={article.id}
                className="w-full text-left p-2 rounded-md hover:bg-accent transition-colors"
                onClick={() => {
                  router.push(`/help/${article.slug}`);
                  setOpen(false);
                }}
              >
                <div className="flex items-center gap-2">
                  <BookOpen className="h-4 w-4 text-primary" />
                  <span className="text-sm font-medium">{article.title}</span>
                </div>
                <p className="text-xs text-muted-foreground mt-1 line-clamp-1">{article.content}</p>
              </button>
            ))}
          </div>
          <div className="p-3 border-t">
            <Button variant="ghost" size="sm" className="w-full justify-start gap-2" onClick={() => { router.push('/support'); setOpen(false); }}>
              <MessageSquare className="h-4 w-4" />Contact Support
            </Button>
          </div>
        </Card>
      )}
    </>
  );
}
