import React, { useEffect, useState } from 'react';
import '../Overview.css'

const TwoTables = () => {
    const [projects, setProjects] = useState([]);
    const [bugs, setBugs] = useState([]);

    useEffect(() => {
        fetchProjects();
        fetchBugs();
    }, []);

    async function fetchProjects() {
        const response = await fetch('http://0.0.0.0:8000/api/v1/project/fetch_all');
        const data = await response.json();
        setProjects(data.projects);
    }

    async function fetchBugs() {
        const response = await fetch('http://0.0.0.0:8000/api/v1/bug/fetch_all');
        const data = await response.json();
        setBugs(data.bugs);
    }

    return (
        <div className="two-tables-container">
            <div className="table-container">
                <h2>Projects</h2>
                <table>
                    <thead>
                    <tr>
                        {/* Add table headers according to your data structure */}
                        <th>Index</th>
                        <th>Name</th>
                        <th>Author</th>
                        <th>Language</th>
                        <th>Parent</th>
                    </tr>
                    </thead>
                    <tbody>
                    {projects.map((project, index) => (
                        <tr key={index}>
                            {/* Render table cells according to your data structure */}
                            <td className="scrollable-cell small-cell">
                                <div className="scrollable-cell-content">{project.index}</div>
                            </td>
                            <td>{project.name}</td>
                            <td>{project.owner}</td>
                            <td>{project.language}</td>
                            <td>{project.parent}</td>
                        </tr>
                    ))}
                    </tbody>
                </table>
            </div>
            <div className="table-container">
                <h2>Bugs</h2>
                <table>
                    <thead>
                    <tr>
                        {/* Add table headers according to your data structure */}
                        <th>Index</th>
                        <th>ID</th>
                        <th>Fix Commits</th>
                        <th>Patch</th>
                        <th>Code</th>
                        <th>V</th>
                    </tr>
                    </thead>
                    <tbody>
                    {bugs.map((bug, index) => (
                        <tr key={index}>
                            {/* Render table cells according to your data structure */}
                            <td className="scrollable-cell small-cell">
                                <div className="scrollable-cell-content">{bug.index}</div>
                            </td>
                            <td className="scrollable-cell">
                                <div className="scrollable-cell-content">{bug.id}</div>
                            </td>
                            <td className="scrollable-cell">
                                <div className="scrollable-cell-content">{bug.fix_commit}</div>
                            </td>
                            <td className="scrollable-cell">
                                <div className="scrollable-cell-content">{bug.patch}</div>
                            </td>
                            <td className="scrollable-cell">
                                <div className="scrollable-cell-content">{bug.code}</div>
                            </td>
                            <td className="scrollable-cell small-cell">
                                <div className="scrollable-cell-content">{bug.verified}</div>
                            </td>
                        </tr>
                    ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default TwoTables;
