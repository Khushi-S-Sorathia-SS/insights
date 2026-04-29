import React from 'react';
import Head from 'next/head';
import FileUpload from '../components/FileUpload';
import ChatWindow from '../components/ChatWindow';

export default function Home() {
  return (
    <>
      <Head>
        <title>Insights Chatbot | Employee Data Analysis</title>
        <meta
          name="description"
          content="AI-powered chatbot for employee dataset analysis"
        />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
        <header className="bg-white shadow-sm">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
            <h1 className="text-3xl font-bold text-gray-900">
              📊 Insights Chatbot
            </h1>
            <p className="text-gray-600 mt-1">
              AI-powered analysis for employee datasets
            </p>
          </div>
        </header>

        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            {/* Upload Section */}
            <div className="lg:col-span-1">
              <div className="bg-white rounded-lg shadow-md p-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-4">
                  📁 Upload Dataset
                </h2>
                <FileUpload />
              </div>
            </div>

            {/* Chat Section */}
            <div className="lg:col-span-3">
              <div className="bg-white rounded-lg shadow-md p-6 h-[600px] flex flex-col">
                <h2 className="text-xl font-semibold text-gray-900 mb-4">
                  💬 Analysis Chat
                </h2>
                <ChatWindow />
              </div>
            </div>
          </div>
        </main>

        <footer className="bg-white shadow-sm mt-12">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 text-center text-gray-600">
            <p>
              Made with ❤️ for data analysis | Employee Dataset Insight Chatbot
              v1.0
            </p>
          </div>
        </footer>
      </div>
    </>
  );
}
