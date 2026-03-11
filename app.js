parseBtn.addEventListener("click", async () => {
    const file = resumeFile.files[0];
    if (!file) {
        alert("Please upload a resume!");
        return;
    }

    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch("http://127.0.0.1:5000/parse-resume", {
        method: "POST",
        body: formData
    });

    const result = await response.json();
    console.log(result);
});