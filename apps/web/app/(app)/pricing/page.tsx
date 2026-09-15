'use client';

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Check } from 'lucide-react';

const plans = [
  {
    name: 'Free',
    price: '$0',
    description: 'For individuals getting started',
    features: ['5 conversations per day', 'Basic AI models', 'Standard support', '1GB memory storage'],
    cta: 'Get Started',
    variant: 'outline' as const,
  },
  {
    name: 'Pro',
    price: '$29',
    period: '/month',
    description: 'For power users and professionals',
    features: ['Unlimited conversations', 'Advanced AI models', 'Priority support', '10GB memory storage', 'Custom integrations', 'Analytics dashboard'],
    cta: 'Start Free Trial',
    variant: 'default' as const,
    highlighted: true,
  },
  {
    name: 'Enterprise',
    price: '$99',
    period: '/month',
    description: 'For teams and organizations',
    features: ['Everything in Pro', 'Dedicated support', 'Custom AI models', 'Unlimited storage', 'SSO & security', 'SLA guarantee'],
    cta: 'Contact Sales',
    variant: 'outline' as const,
  },
];

export default function PricingPage() {
  return (
    <div className="space-y-6">
      <div className="text-center">
        <h1 className="text-3xl font-bold tracking-tight">Pricing</h1>
        <p className="mt-2 text-muted-foreground">Choose the plan that fits your needs.</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {plans.map((plan) => (
          <Card key={plan.name} className={`p-6 ${plan.highlighted ? 'border-primary shadow-lg' : ''}`}>
            <div className="space-y-4">
              <div>
                <h3 className="text-xl font-bold">{plan.name}</h3>
                <p className="text-sm text-muted-foreground">{plan.description}</p>
              </div>

              <div className="flex items-baseline gap-1">
                <span className="text-4xl font-bold">{plan.price}</span>
                <span className="text-muted-foreground">{plan.period}</span>
              </div>

              <Button variant={plan.variant} className="w-full">
                {plan.cta}
              </Button>

              <ul className="space-y-3">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-2 text-sm">
                    <Check className="h-4 w-4 text-primary mt-0.5 shrink-0" />
                    {feature}
                  </li>
                ))}
              </ul>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
