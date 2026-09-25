'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Loader2, ArrowLeft, ThumbsUp, ThumbsDown, HelpCircle } from 'lucide-react';
import { api } from '@/lib/api';
import { HelpArticle } from '@/lib/api';
import Link from 'next/link';

export default function HelpArticlePage() {
  const params = useParams();
  const slug = params.slug as string;
  const [article, setArticle] = useState<HelpArticle | null>(null);
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState<'helpful' | 'not_helpful' | null>(null);

  useEffect(() => {
    loadArticle();
  }, [slug]);

  const loadArticle = async () => {
    setLoading(true);
    try {
      const data = await api.searchHelpArticles(slug);
      const found = data.articles?.find((a: HelpArticle) => a.slug === slug) || data.article;
      if (found) {
        setArticle(found);
        await api.markArticleHelpful(found.id, true);
      }
    } catch {
      setArticle(null);
    } finally {
      setLoading(false);
    }
  };

  const handleFeedback = async (helpful: boolean) => {
    if (!article) return;
    setFeedback(helpful ? 'helpful' : 'not_helpful');
    await api.markArticleHelpful(article.id, helpful);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!article) {
    return (
      <div className="space-y-6">
        <Link href="/help">
          <Button variant="ghost" size="sm"><ArrowLeft className="h-4 w-4 mr-2" />Back to Help Center</Button>
        </Link>
        <Card className="p-12 text-center">
          <HelpCircle className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="text-lg font-medium">Article not found</h3>
          <p className="text-muted-foreground">The article you are looking for does not exist.</p>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <Link href="/help">
        <Button variant="ghost" size="sm"><ArrowLeft className="h-4 w-4 mr-2" />Back to Help Center</Button>
      </Link>

      <Card className="p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <Badge variant="secondary" className="mb-2">{article.category}</Badge>
            <h1 className="text-2xl font-bold">{article.title}</h1>
            <p className="text-sm text-muted-foreground mt-1">{article.views} views</p>
          </div>
        </div>
        <div className="mt-6 prose dark:prose-invert max-w-none">
          <p className="whitespace-pre-wrap text-sm leading-relaxed">{article.content}</p>
        </div>
        <div className="mt-8 pt-4 border-t">
          <p className="text-sm font-medium mb-2">Was this article helpful?</p>
          <div className="flex gap-2">
            <Button
              variant={feedback === 'helpful' ? 'default' : 'outline'}
              size="sm"
              onClick={() => handleFeedback(true)}
            >
              <ThumbsUp className="h-4 w-4 mr-2" />Yes
            </Button>
            <Button
              variant={feedback === 'not_helpful' ? 'default' : 'outline'}
              size="sm"
              onClick={() => handleFeedback(false)}
            >
              <ThumbsDown className="h-4 w-4 mr-2" />No
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
