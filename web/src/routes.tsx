import type { RouteRecord } from 'vite-react-ssg'
import Layout from './components/Layout'
import { insights, legalOrder } from './lib/content'

export const routes: RouteRecord[] = [
  {
    path: '/',
    element: <Layout />,
    entry: 'src/components/Layout.tsx',
    children: [
      { index: true, lazy: () => import('./pages/Home') },
      { path: 'approach', lazy: () => import('./pages/Approach') },
      { path: 'team', lazy: () => import('./pages/Team') },
      { path: 'insights', lazy: () => import('./pages/Insights') },
      {
        path: 'insights/:slug',
        lazy: () => import('./pages/InsightArticle'),
        getStaticPaths: () => insights.map((a) => `insights/${a.slug}`),
      },
      { path: 'contact', lazy: () => import('./pages/Contact') },
      {
        path: 'legal/:slug',
        lazy: () => import('./pages/Legal'),
        getStaticPaths: () => legalOrder.map((s) => `legal/${s}`),
      },
      { path: 'login', lazy: () => import('./pages/Login') },
      { path: '*', lazy: () => import('./pages/NotFound') },
    ],
  },
]
