import React from "react";
import {AppBar, Button, Toolbar, Typography, Box} from "@mui/material";
import {useNavigate} from "react-router-dom";

const TopBar = () => {
    const navigate = useNavigate();
    return (
        <AppBar position="static">
            <Toolbar>
                <Typography variant="h6">Detection of Cloned Vulnerabilities</Typography>
                <Box sx={{flexGrow: 1 }} />
                <Button variant="filled" onClick={() => navigate("/")}>
                    overview
                </Button>
                <Button variant="filled" onClick={() => navigate("/prepare_detection")}>
                    prepare detection
                </Button>
                <Button variant="filled" onClick={() => navigate("/detection_result")}>
                    detection result
                </Button>
            </Toolbar>
        </AppBar>
    );
}

export default TopBar;
