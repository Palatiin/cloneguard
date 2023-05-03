// File: src/component/pages/Overview.js
// Project: Monitoring and Reporting Tool for Cloned Vulnerabilities across Open-Source Projects
// Author: Matus Remen (xremen01@stud.fit.vutbr.cz)
// Date: 2023-04-29
// Description: Root component of the web application.

import logo from './logo.svg';
import './App.css';
import {BrowserRouter, Route, Routes} from "react-router-dom";
import Overview from "./component/pages/Overview";
import TopBar from "./component/TopBar";
import {Box, Container} from "@mui/material";
import {createTheme, ThemeProvider} from "@mui/material/styles";
import CssBaseline from '@mui/material/CssBaseline';
import PrepareDetection from "./component/pages/PrepareDetection";
import DetectionResult from "./component/pages/DetectionResult";
import {ToastContainer} from "react-toastify";
import "react-toastify/dist/ReactToastify.css";

const theme = createTheme({
    palette: {
    }
})

function App() {
    return (
        <ThemeProvider theme={theme}>
            <CssBaseline/>
            <BrowserRouter>
                <div className="App">
                    <TopBar/>
                    <Container maxWidth="xl">
                        <Box mt={2}>
                            <Routes>
                                <Route path="/" element={<Overview/>}/>
                                <Route path="/prepare_detection" element={<PrepareDetection/>}/>
                                <Route path="/detection_result" element={<DetectionResult/>}/>
                            </Routes>
                        </Box>
                    </Container>
                </div>
            </BrowserRouter>
            <ToastContainer
                position="bottom-right"
            />

        </ThemeProvider>
    );
}

export default App;
