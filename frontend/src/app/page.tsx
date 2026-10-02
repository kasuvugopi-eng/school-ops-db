import Link from 'next/link';

export default function Home() {
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center">
      <header className="w-full max-w-6xl p-6 flex justify-between items-center">
        <h1 className="text-2xl font-bold text-indigo-700">SchoolOps</h1>
        <nav className="gap-4 flex">
          <Link href="/login" className="text-slate-600 hover:text-indigo-600 font-medium px-4 py-2">Login</Link>
          <Link href="/register" className="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700 font-medium">Register</Link>
        </nav>
      </header>
      
      <main className="flex-1 w-full max-w-6xl p-6 flex flex-col items-center mt-12 text-center">
        <h2 className="text-5xl font-extrabold text-slate-900 tracking-tight mb-6">School Operations, Simplified with AI</h2>
        <p className="text-xl text-slate-600 max-w-2xl mb-12">Automate workflows, empower teachers, and engage students with our intelligent platform designed for modern schools.</p>
        
        <div className="grid md:grid-cols-3 gap-8 w-full mt-12">
          <div className="bg-white p-8 rounded-xl shadow-sm border border-slate-100 flex flex-col items-center">
            <div className="text-4xl mb-4">📄</div>
            <h3 className="text-lg font-semibold text-slate-900 mb-2">Smart Document Parsing</h3>
            <p className="text-slate-600 text-center">Turn PDFs and syllabi into structured assignments automatically.</p>
          </div>
          <div className="bg-white p-8 rounded-xl shadow-sm border border-slate-100 flex flex-col items-center">
            <div className="text-4xl mb-4">📱</div>
            <h3 className="text-lg font-semibold text-slate-900 mb-2">Telegram Integration</h3>
            <p className="text-slate-600 text-center">Seamless communication for students and parents on a platform they love.</p>
          </div>
          <div className="bg-white p-8 rounded-xl shadow-sm border border-slate-100 flex flex-col items-center">
            <div className="text-4xl mb-4">🔔</div>
            <h3 className="text-lg font-semibold text-slate-900 mb-2">Smart Reminders</h3>
            <p className="text-slate-600 text-center">Automated nudges based on performance and upcoming deadlines.</p>
          </div>
        </div>
      </main>
    </div>
  );
}
