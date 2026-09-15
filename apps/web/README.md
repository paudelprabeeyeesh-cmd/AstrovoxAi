# AstrovoxAI Frontend

## Tech Stack
- Next.js 16 (App Router)
- React 19
- TypeScript
- Tailwind CSS + shadcn/ui
- Zustand + TanStack Query
- Vercel AI SDK
- NextAuth.js
- Framer Motion
- React Markdown + Shiki
- Recharts

## Getting Started

### Prerequisites
- Node.js 18+
- npm or yarn

### Installation
```bash
cd apps/web
npm install
```

### Environment Variables
Copy `.env.local` and fill in:
- NEXT_PUBLIC_API_URL - Backend API URL
- NEXTAUTH_SECRET - NextAuth secret
- NEXTAUTH_URL - Frontend URL
- OPENAI_API_KEY - OpenAI key
- STRIPE_PUBLISHABLE_KEY - Stripe key

### Development
```bash
npm run dev
```
Open http://localhost:3000

### Build
```bash
npm run build
npm start
```

## Project Structure
See FRONTEND_BLUEPRINT.md for complete structure.

## Key Features
- Landing page with pricing
- Authentication (login, register, forgot password)
- Chat with streaming
- Dashboard with usage stats
- Settings (profile, appearance, billing, API keys)
- Memory panel
- Library
- Pricing page

## Deployment
Deploy to Vercel:
```bash
vercel --prod
```
