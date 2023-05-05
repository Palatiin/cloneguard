// File: src/component/TopBar.js
// Project: Monitoring and Reporting Tool for Cloned Vulnerabilities across Open-Source Projects
// Author: Matus Remen (xremen01@stud.fit.vutbr.cz)
// Date: 2023-04-29
// Description: Implementation of the menu bar.

import React from "react";
import {AppBar, Button, Toolbar, Typography, Box} from "@mui/material";
import {useNavigate} from "react-router-dom";

const TopBar = () => {
    const navigate = useNavigate();
    return (
        <AppBar position="static">
            <Toolbar>
                <Typography variant="h6" style={{ fontWeight: 'bold' }}>Detection of Cloned Vulnerabilities</Typography>
                <Box sx={{flexGrow: 1 }} />
                <Button variant="filled" onClick={() => navigate("/")} style={{ fontWeight: 'bold' }}>
                    overview
                </Button>
                <Button variant="filled" onClick={() => navigate("/prepare_detection")} style={{ fontWeight: 'bold' }}>
                    prepare detection
                </Button>
                <Button variant="filled" onClick={() => navigate("/detection_result")} style={{ fontWeight: 'bold' }}>
                    detection result
                </Button>
                <Button variant="filled" href="http://localhost:8000/api/v1/docs" style={{ fontWeight: 'bold' }}>
                   api docs
                </Button>
            </Toolbar>
        </AppBar>
    );
}

export default TopBar;
