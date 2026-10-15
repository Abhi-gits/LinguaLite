import Footer from './components/Footer'
import Header from './components/Header'
import Translator from './components/Translator'

export default function App() {
  return (
    <div className="flex min-h-svh flex-col">
      <Header />
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8 sm:px-6">
        <h1 className="sr-only">LinguaLite multilingual writing assistant</h1>
        <Translator />
      </main>
      <Footer />
    </div>
  )
}
