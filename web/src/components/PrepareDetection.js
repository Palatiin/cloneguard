import React, { useState } from 'react';
import '../PrepareDetection.css';

const Prepare = () => {
    const [input1, setInput1] = useState('');
    const [input2, setInput2] = useState('');
    const [commits, setCommits] = useState([]);
    const [patchCode, setPatchCode] = useState('');
    const [fixCommit, setFixCommit] = useState('');
    const [method, setMethod] = useState('');
    const [date, setDate] = useState('');

    const handleChange1 = (e) => setInput1(e.target.value);
    const handleChange2 = (e) => setInput2(e.target.value);

    const handleSearchSubmit = async (e) => {
        e.preventDefault();

        // Send a POST request to the API with the content of the two input fields
        const requestOptions = {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ bug_id: input1, project_name: input2 }),
        };

        try {
            const response = await fetch('http://0.0.0.0:8000/api/v1/detection/search', requestOptions);
            const data = await response.json();
            console.log(data);

            // Store the response data in the state variables
            setCommits(data.search_result.commits);
            setPatchCode(atob(data.search_result.patch));
        } catch (error) {
            console.error('Error:', error);
        }
    };

    const handleExecuteSubmit = async (e) => {
        e.preventDefault()

        const formattedDate = date ? new Date(date).toISOString().slice(0, 10) : '';

        const payload = {
            bug_id: input1,
            project_name: input2,
            commit: fixCommit,
            patch: btoa(patchCode),
            method: method,
            date: formattedDate,
        };

        try {
            const response = await fetch('http://0.0.0.0:8000/api/v1/detection/execute', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
            });

            if (response.ok) {
                console.log('Data submitted successfully');
            } else {
                console.error('Error submitting data:', response.statusText);
            }
        } catch (error) {
            console.error('Error submitting data:', error);
        }
    };

    return (
        <div className="prepare-container">
            <div className="content">
                <form onSubmit={handleSearchSubmit} className="form-container">
                    <div className="input-container">
                        <label htmlFor="input1">Input 1:</label>
                        <input type="text" id="input1" value={input1} onChange={handleChange1} />
                    </div>
                    <div className="input-container">
                        <label htmlFor="input2">Input 2:</label>
                        <input type="text" id="input2" value={input2} onChange={handleChange2} />
                    </div>
                    <button type="submit">Search</button>
                </form>

                <div className="prepare-container">
                    {/* ... form code ... */}

                    <div className="response-container">
                        <div className="commits-container">
                            <h3>Commits</h3>
                            <table className="commits-table">
                                <thead>
                                <tr>
                                    <th>Commit</th>
                                </tr>
                                </thead>
                                <tbody>
                                {commits.map((commit, index) => (
                                    <tr key={index}>
                                        <td>{commit}</td>
                                    </tr>
                                ))}
                                </tbody>
                            </table>
                        </div>

                        <div className="patch-code-container">
                            <h3>Patch Code</h3>
                            <textarea
                                value={patchCode}
                                onChange={(e) => setPatchCode(e.target.value)}
                                rows="30" // Set the number of visible rows
                                cols="200" // Set the number of visible columns
                            ></textarea>
                        </div>
                    </div>
                </div>
            </div>

            <div className="bottom-inputs-container">
                <div className="input-container">
                    <label htmlFor="fixCommit">Fix Commit:</label>
                    <input type="text" id="fixCommit" value={fixCommit} onChange={(e) => setFixCommit(e.target.value)} />
                </div>
                <div className="input-container">
                    <label htmlFor="method">Method:</label>
                    <input type="text" id="method" value={method} onChange={(e) => setMethod(e.target.value)} />
                </div>
                <div className="input-container">
                    <label htmlFor="date">Date:</label>
                    <input type="date" id="date" value={date} onChange={(e) => setDate(e.target.value)} />
                </div>
                <button onClick={handleExecuteSubmit}>Execute</button>
            </div>
        </div>
    );
};

export default Prepare;
