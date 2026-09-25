'use client';

import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Loader2, Search, BookOpen, ThumbsUp, ThumbsDown, HelpCircle } from 'lucide-react';
import { api } from '@/lib/api';
import { HelpArticle } from '@/lib/api';

const CATEGORIES = ['Getting Started', 'Account', 'Billing', 'Technical', 'API', 'Integrations'];

export default function HelpCenterPage() {
  const [articles, setArticles] = useState<HelpArticle[]>([]);
  const [filtered, setFiltered] = useState<HelpArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  useEffect(() => {
    loadArticles();
  }, []);

  useEffect(() => {
    let result = articles;
    if (selectedCategory) {
      result = result.filter(a => a.category === selectedCategory);
    }
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      result = result.filter(a => a.title.toLowerCase().includes(q) || a.content.toLowerCase().includes(q));
    }
    setFiltered(result);
  }, [articles, searchQuery, selectedCategory]);

  const loadArticles = async () => {
    setLoading(true);
    try {
      const data = await api.getHelpArticles();
      setArticles(data.articles || []);
    } catch {
      setArticles([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Help Center</h1>
        <p className="text-muted-foreground">Find answers and learn how to get the most out of AstrovoxAi.</p>
      </div>

      <div className="flex gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search help articles..."
            className="pl-8"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      <div className="flex gap-2 flex-wrap">
        <Badge
          variant={selectedCategory === null ? 'default' : 'secondary'}
          className="cursor-pointer"
          onClick={() => setSelectedCategory(null)}
        >
          All
        </Badge>
        {CATEGORIES.map((cat) => (
          <Badge
            key={cat}
            variant={selectedCategory === cat ? 'default' : 'secondary'}
            className="cursor-pointer"
            onClick={() => setSelectedCategory(cat)}
          >
            {cat}
          </Badge>
        ))}
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : filtered.length === 0 ? (
        <Card className="p-12 text-center">
          <HelpCircle className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="text-lg font-medium">No articles found</h3>
          <p className="text-muted-foreground">Try adjusting your search or filters.</p>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filtered.map((article) => (
            <Card key={article.id} className="p-4 hover:shadow-md transition-shadow">
              <a href={`/help/${article.slug}`} className="block">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <BookOpen className="h-4 w-4 text-primary" />
                    <h3 className="font-semibold text-sm">{article.title}</h3>
                  </div>
                  <Badge variant="secondary" className="text-xs">{article.category}</Badge>
                </div>
                <p className="mt-2 text-sm text-muted-foreground line-clamp-2">{article.content.slice(0, 150)}...</p>
                <div className="mt-3 flex items-center gap-4 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <ThumbsUp className="h-3 w-3" /> {article.helpful_count}
                  </span>
                  <span className="flex items-center gap-1">
                    <ThumbsDown className="h-3 w-3" /> {article.not_helpful_count}
                  </span>
                  <span>{article.views} views</span>
                </div>
              </a>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
