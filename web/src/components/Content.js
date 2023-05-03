import React from 'react';
import { Route, Routes } from 'react-router-dom';
import Overview from './Overview';
import PrepareDetection from './PrepareDetection';
import DetectionResults from './DetectionResults';

function Content() {
    return (
        <main>
            <Routes>
                <Route path="/" element={<Overview />} />
                <Route path="/prepare" element={<PrepareDetection />} />
                <Route path="/results" element={<DetectionResults />} />
            </Routes>
        </main>
    );
}

export default Content;
