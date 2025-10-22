export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <h1 className="text-4xl font-bold mb-4">
        Fantasy Football AI Manager
      </h1>
      <p className="text-xl text-gray-600">
        Your intelligent assistant for dominating your league
      </p>
      <div className="mt-8 text-sm text-gray-500">
        <p>Backend API: <a href="http://localhost:8000/docs" className="text-blue-500 hover:underline" target="_blank">http://localhost:8000/docs</a></p>
      </div>
    </main>
  )
}
