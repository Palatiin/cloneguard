import React, { useEffect, useState, useRef } from "react";
import "../DetectionResults.css";

function DetectionResults() {
    const [logs, setLogs] = useState("");
    const [detectionResults, setDetectionResults] = useState([]);
    const textareaRef = useRef(null);

    const fetchStatus = async () => {
        try {
            const response = await fetch("http://0.0.0.0:8000/api/v1/detection/status");
            const data = await response.json();
            setLogs(data.status.logs);
            setDetectionResults(data.status.detection_results)
        } catch (error) {
            console.log(error);
        }
    };

    useEffect(() => {
        const interval = setInterval(() => {
            fetchStatus();
        }, 5000);
        return () => clearInterval(interval);
    }, []);

    useEffect(() => {
        // Scroll the textarea to the bottom
        textareaRef.current.scrollTop = textareaRef.current.scrollHeight;
    }, [logs]);

    return (
        <div className="response-container">
            <div>
                <h2>Logs</h2>
                <textarea
                    ref={textareaRef}
                    readOnly value={logs}
                    rows="45" // Set the number of visible rows
                    cols="300" // Set the number of visible columns
                ></textarea>
            </div>
            <div className="DetectionResults">
                <h2>Detection Results</h2>
                <table>
                    <thead>
                    <tr>
                        <th>Project</th>
                        <th>Vulnerable</th>
                        <th>Confidence</th>
                        <th>Location</th>
                    </tr>
                    </thead>
                    <tbody>
                    {detectionResults.map((result, index) => (
                        <tr key={index}>
                            <td>{result.project_name}</td>
                            <td>{result.vulnerable}</td>
                            <td>{result.confidence}</td>
                            <td>{result.location}</td>
                        </tr>
                    ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

export default DetectionResults;
