// File: src/component/pages/DetectionResults.js
// Project: Monitoring and Reporting Tool for Cloned Vulnerabilities across Open-Source Projects
// Author: Matus Remen (xremen01@stud.fit.vutbr.cz)
// Date: 2023-04-29
// Description: Implementation of the page displaying detection results and logs.

import React, {useEffect, useState, useRef} from "react";
import {
    Grid,
    Paper,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    TextField,
    Typography
} from "@mui/material";
import {load} from "../../api";
import styled from "@emotion/styled";
import {tableCellClasses} from "@mui/material/TableCell";

const StyledTableCell = styled(TableCell)(({ theme }) => ({
  [`&.${tableCellClasses.head}`]: {
    backgroundColor: theme.palette.common.black,
    color: theme.palette.common.white,
  },
  [`&.${tableCellClasses.body}`]: {
    fontSize: 14,
  },
}));

const DetectionResult = () => {
    const textFieldRef = useRef(null);
    const [logs, setLogs] = useState("");
    const [detectionResults, setDetectionResults] = useState([]);

    useEffect(() => {
        const interval = setInterval(() => {
            reload();
        }, 5000);

        return () => clearInterval(interval);
    }, []);

    const reload = () => {
         load("/detection/status")
            .then((resp) => {
                setLogs(resp.data.status.logs);
                setDetectionResults(resp.data.status.detection_results);
            });
    }

    useEffect(() => {
        reload();
    }, []);

    useEffect(() => {
        if (textFieldRef.current) {
            textFieldRef.current.scrollTop = textFieldRef.current.scrollHeight;
        }
    }, [logs]);

    return (
        <Grid container spacing={2}>
            <Grid item xs={6}>
                <Paper>
                    <Typography variant="h6" p={1}>Logs</Typography>
                    <TextField
                        inputRef={textFieldRef}
                        multiline
                        rows={20}
                        fullWidth={true}
                        value={logs}
                        disabled={true}
                    />
                </Paper>
            </Grid>
            <Grid item xs={6}>
                <Paper>
                    <Typography variant="h6" p={1}>Detection Results</Typography>
                    <TableContainer>
                    <Table>
                        <TableHead>
                            <TableRow>
                                <StyledTableCell><Typography>Project name</Typography></StyledTableCell>
                                <StyledTableCell><Typography>Vulnerable</Typography></StyledTableCell>
                                <StyledTableCell><Typography>Confidence</Typography></StyledTableCell>
                                <StyledTableCell><Typography>Location</Typography></StyledTableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {detectionResults.map((result, index) => (
                                <TableRow key={index}>
                                    <StyledTableCell>{result.project_name}</StyledTableCell>
                                    <StyledTableCell>{result.vulnerable}</StyledTableCell>
                                    <StyledTableCell>{result.confidence}</StyledTableCell>
                                    <StyledTableCell>{result.location}</StyledTableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </TableContainer>
                </Paper>
            </Grid>
        </Grid>
    )
}

export default DetectionResult