import React from 'react';
import type { Metadata } from 'next';
import './globals.css';
import { AdminSidebar }  from './_components/AdminSidebar';
import { getAuthUser }   from '@/lib/supabase-server';

export const metadata: Metadata = {
  title:       'Admin — theNewslane',
  description: 'theNewslane Admin Panel',
};

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const user = await getAuthUser();

  return (
    <html lang="en">
      <body className={user ? 'flex h-screen overflow-hidden bg-slate-50' : 'bg-slate-900 min-h-screen'}>
        {user ? (
          <>
            <AdminSidebar userEmail={user.email ?? ''} />
            <main className="flex-1 overflow-y-auto focus:outline-none">
              {children}
            </main>
          </>
        ) : (
          children
        )}
      </body>
    </html>
  );
}
