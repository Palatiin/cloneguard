// File: src/component/pages/PrepareDetection.js
// Project: Monitoring and Reporting Tool for Cloned Vulnerabilities across Open-Source Projects
// Author: Matus Remen (xremen01@stud.fit.vutbr.cz)
// Date: 2023-04-29
// Description: Implementation of the page where detection can be started.

import React, {useEffect, useState} from "react";
import {
    Box,
    Button,
    Divider,
    Grid,
    IconButton,
    List,
    ListItem, ListItemButton,
    ListItemText,
    Paper,
    Stack,
    TextField,
    Typography
} from "@mui/material";
import { DatePicker } from "@mui/x-date-pickers";
import { LocalizationProvider } from '@mui/x-date-pickers';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs'
import {load, post} from "../../api";
import dayjs from 'dayjs';
import {useNavigate} from "react-router-dom";



const PrepareDetection = () => {
    const navigate = useNavigate();
    const [commits, setCommits] = useState([]);
    const [selectedCommit, setSelectedCommit] = useState(null);
    const [patch, setPatch] = useState("");

    const [vulnId, setVulnId] = useState("");
    const [project, setProject] = useState("");

    const [method, setMethod] = useState("");
    const [commitId, setCommitId] = useState("");
    const [selectedDate, setSelectedDate] = useState(null);

   const search = () => {
       post("/detection/search", {bug_id: vulnId, project_name: project})
           .then((resp) => {
               let commits = resp.data.search_result.commits;
               setCommits(commits);
               setPatch(atob(resp.data.search_result.patch));
               setSelectedCommit(commits[0]);
               setCommitId(commits[0]);
           });
   }

   const selectCommit = (commit) => {
         setSelectedCommit(commit);
         setCommitId(commit);
         post("/detection/show_commit", {project_name: project, commit: commit})
              .then((resp) => {
                    setPatch(atob(resp.data.commit.patch));
              });
   }

   const detect = () => {
         let date = selectedDate ? dayjs(selectedDate).format("YYYY-MM-DD") : "";
         post("/detection/execute", {
             bug_id: vulnId,
             project_name: project,
             commit: commitId,
             patch: btoa(patch),
             method: method,
             date: date
         })
              .then((resp) => {
                    navigate("/detection_result");
              });
   }

    return (
        <Grid container spacing={2}>
            <Grid item xs={12}>
                <Stack direction="row" spacing={2}>
                    <TextField
                        size="small"
                        id="vulnId"
                        label="VulnID"
                        variant="outlined"
                        value={vulnId}
                        onChange={(e) => setVulnId(e.target.value)}
                    />
                    <TextField
                        size="small"
                        id="project"
                        label="Source project"
                        variant="outlined"
                        value={project}
                        onChange={(e) => setProject(e.target.value)}
                    />
                    <Button variant={"contained"} onClick={search}>Search</Button>
                </Stack>
            </Grid>
            <Grid item xs={4}>
                <Paper>
                    <Typography variant="h6" p={1}>Candidate commits</Typography>
                    <Divider />
                    <List dense={true}>
                        {commits && commits.map((commit) => (
                            <ListItemButton
                                key={commit}
                                onClick={() => selectCommit(commit)}
                                selected={selectedCommit === commit}
                            >
                                <ListItemText
                                    primary={commit}
                                />
                            </ListItemButton>
                        ))}
                    </List>
                </Paper>
            </Grid>
            <Grid item xs={8}>
                <Paper>
                    <Typography variant="h6" p={1}>Path/code for clone detection</Typography>
                </Paper>
                <TextField
                    multiline
                    fullWidth={true}
                    with="100%"
                    rows={20}
                    value={patch}
                    onChange={(e) => setPatch(e.target.value)}
                />
            </Grid>
            <Grid item xs={4}/>
            <Grid item xs={8}>
                <Stack direction="row" spacing={2}>
                    <TextField
                        size="small"
                        id="commitId"
                        label="Fix commit id"
                        variant="outlined"
                        value={commitId}
                        onChange={(e) => setCommitId(e.target.value)}
                    />
                    <TextField
                        size="small"
                        id="method"
                        label="method"
                        variant="outlined"
                        value={method}
                        onChange={(e) => setMethod(e.target.value)}
                    />
                    <LocalizationProvider dateAdapter={AdapterDayjs}>
                        <DatePicker
                            label="Select Date"
                            value={selectedDate && dayjs(selectedDate)}
                            size="small"
                            onChange={(value) => setSelectedDate(value)}
                            slotProps={{ textField: { size: 'small' } }}
                        />

                    </LocalizationProvider>
                    <Button variant={"contained"} size="small" onClick={detect}>Detect</Button>
                </Stack>
            </Grid>
        </Grid>
    );
}

export default PrepareDetection;
