// File: src/component/pages/Overview.js
// Project: Monitoring and Reporting Tool for Cloned Vulnerabilities across Open-Source Projects
// Author: Matus Remen (xremen01@stud.fit.vutbr.cz)
// Date: 2023-04-29
// Description: Implementation of the overview page displaying list of registered projects and stored bugs.

import React, {useState, useEffect} from "react";
import styled from "@emotion/styled";
import {
    Container,
    Stack,
    Divider,
    Typography,
    TableContainer,
    TableCell,
    TableRow,
    TableHead,
    Table, TableBody, Paper, TextField, Button, InputLabel, Select, MenuItem, FormControl, IconButton, Collapse, Box
} from "@mui/material";
import { tableCellClasses } from '@mui/material/TableCell';
import {load, post} from "../../api";
import {toast} from "react-toastify";
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp';

const StyledTableCell = styled(TableCell)(({ theme }) => ({
  [`&.${tableCellClasses.head}`]: {
    backgroundColor: theme.palette.common.black,
    color: theme.palette.common.white,
  },
  [`&.${tableCellClasses.body}`]: {
    fontSize: 14,
  },
}));


function Row(props) {
  const { bug } = props;
  const [open, setOpen] = React.useState(false);

  return (
      <React.Fragment>
          <TableRow sx={{ '& > *': { borderBottom: 'unset' } }}>

              <StyledTableCell>{bug.index}</StyledTableCell>
              <StyledTableCell>{bug.id}</StyledTableCell>
              <StyledTableCell>{bug.fix_commit}</StyledTableCell>
              <StyledTableCell>{bug.verified ? 'Y': ''}</StyledTableCell>
              <StyledTableCell>
                  <IconButton
                      aria-label="expand row"
                      onClick={() => setOpen(!open)}
                      sx={{
                          mt: -5,
                          mb: -5,
                      }}
                  >
                      {open ? <KeyboardArrowUpIcon/> : <KeyboardArrowDownIcon />}
                  </IconButton>
              </StyledTableCell>
          </TableRow>
          <TableRow>
              <TableCell style={{ paddingBottom: 0, paddingTop: 0 }} colSpan={5}>
                  <Collapse in={open} timeout="auto" unmountOnExit>
                      <Box>
                          <Box height={10}/>
                          <Typography>
                              Patch
                          </Typography>
                          <TextField
                              multiline
                              fullWidth
                              value={atob(bug.patch)}
                              rows={5}
                              disabled={true}
                          />
                          <Typography>
                              Code
                          </Typography>
                          <TextField
                              multiline
                              fullWidth
                              value={atob(bug.code)}
                              rows={5}
                              disabled={true}
                          />
                          <Box height={10}/>
                      </Box>
                  </Collapse>
              </TableCell>
          </TableRow>
      </React.Fragment>
  );
}


const Overview = () => {
    const [bugs, setBugs] = useState([]);
    const [projects, setProjects] = useState([]);

    const [url, setUrl] = useState("");
    const [language, setLanguage] = useState("");
    const [parent, setParent] = useState("");

    const [id, setId] = useState("");
    const [patch, setPatch] = useState("");
    const [fixCommit, setFixCommit] = useState("");
    const [method, setMethod] = useState("blockscope");

    const addProject = () => {
        post("/project/register", {
            url: url,
            language: language,
            parent: parent
        })
            .then((resp) => {
                reload();
                console.log(resp)
                if(resp.success) {
                    toast.success("Project added");
                }
                else {
                    toast.error("Project add failed");
                }
            });
    }

    const updateBug = () => {
        post("/bug/update", {
            id: id,
            patch: btoa(patch),
            fix_commit: fixCommit ? [fixCommit] : "",
            method: method,
        })
            .then((resp) => {
                reload();
                if(resp.success) {
                    toast.success("Bug updated");
                }
                else {
                    toast.error("Bug update failed");
                }
            });
    }

    const reload = () => {
        load("/bug/fetch_all")
            .then((resp) => {
                setBugs(resp.data.bugs);
            });
        load("/project/fetch_all")
            .then((resp) => {
                setProjects(resp.data.projects);
            });
    }

    useEffect(() => {
        reload();
    }, []);


    return (
        <Stack
            direction="row"
            spacing={3}
            divider={<Divider orientation="vertical" flexItem/>}
            justifyContent="space-around"
        >
            <Paper
                sx={{
                    width: "100%",
                    height: "100%"
                }}
            >
                <Typography variant="h6" p={1}>Projects</Typography>
                <Paper sx={{ width: '100%', overflow: 'hidden' }}>
                    <TableContainer sx={{ maxHeight: 600}}>
                        <Table stickyHeader>
                            <TableHead>
                                <TableRow>
                                    <StyledTableCell><Typography>ID</Typography></StyledTableCell>
                                    <StyledTableCell><Typography>Name</Typography></StyledTableCell>
                                    <StyledTableCell><Typography>Owner</Typography></StyledTableCell>
                                    <StyledTableCell><Typography>Language</Typography></StyledTableCell>
                                    <StyledTableCell><Typography>Parent</Typography></StyledTableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {projects && projects.map((project) => (
                                    <TableRow key={project.index}>
                                        <StyledTableCell>{project.index}</StyledTableCell>
                                        <StyledTableCell>{project.name}</StyledTableCell>
                                        <StyledTableCell>{project.owner}</StyledTableCell>
                                        <StyledTableCell>{project.language}</StyledTableCell>
                                        <StyledTableCell>{project.parent}</StyledTableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </TableContainer>
                </Paper>
                <Stack direction="row" spacing={2} m={2}>
                    <TextField
                        size="small"
                        id="url"
                        label="URL"
                        variant="outlined"
                        value={url}
                        onChange={(e) => setUrl(e.target.value)}
                    />
                    <TextField
                        size="small"
                        id="language"
                        label="Language"
                        variant="outlined"
                        value={language}
                        onChange={(e) => setLanguage(e.target.value)}
                    />
                    <TextField
                        size="small"
                        id="parent"
                        label="Parent"
                        variant="outlined"
                        value={parent}
                        onChange={(e) => setParent(e.target.value)}
                    />
                    <Button variant={"contained"} size="small" onClick={addProject}>add</Button>
        </Stack>
            </Paper>
            <Paper
                sx={{
                    width: "100%",
                    height: "100%"
                }}
            >
                <Typography variant="h6" p={1}>Bugs</Typography>

                <Paper sx={{ width: '100%', overflow: 'hidden' }}>
                <TableContainer sx={{ maxHeight: 600}} >
                    <Table stickyHeader>
                        <TableHead>
                            <TableRow>
                                <StyledTableCell><Typography>Index</Typography></StyledTableCell>
                                <StyledTableCell><Typography>ID</Typography></StyledTableCell>
                                <StyledTableCell><Typography>Fix Commit</Typography></StyledTableCell>
                                <StyledTableCell><Typography>Verified</Typography></StyledTableCell>
                                <StyledTableCell><Typography>Show more</Typography></StyledTableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {bugs && bugs.map((bug) => (
                                <Row key={bug.index} bug={bug}/>
                            ))}
                        </TableBody>
                    </Table>
                </TableContainer>
                </Paper>
                <Stack direction="row" spacing={2} m={2}>
                    <TextField
                        size="small"
                        id="id"
                        label="ID"
                        variant="outlined"
                        value={id}
                        onChange={(e) => setId(e.target.value)}
                    />
                    <TextField
                        size="small"
                        id="patch"
                        label="Patch/Code"
                        variant="outlined"
                        value={patch}
                        onChange={(e) => setPatch(e.target.value)}
                    />
                    <TextField
                        size="small"
                        id="fixCommit"
                        label="Fix Commit"
                        variant="outlined"
                        value={fixCommit}
                        onChange={(e) => setFixCommit(e.target.value)}
                    />
                    <FormControl>
                        <InputLabel id="method-label">Method</InputLabel>
                        <Select
                            labelId="method-label"
                            id="method"
                            value={method}
                            label="Method"
                            onChange={(e) => setMethod(e.target.value)}
                            size={"small"}
                        >
                            <MenuItem value={"blockscope"}>Blockscope</MenuItem>
                            <MenuItem value={"simian"}>Simian</MenuItem>
                        </Select>
                    </FormControl>

                    <Button variant={"contained"} size="small" onClick={updateBug}>Update</Button>
                </Stack>
            </Paper>
        </Stack>
    );
}

export default Overview;
