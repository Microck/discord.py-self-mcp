import fs from "node:fs"
import path from "node:path"

const [, , nextVersion] = process.argv

if (!nextVersion) {
  throw new Error("Missing version argument")
}

const root = process.cwd()

const serverPath = path.join(root, "server.json")
const server = JSON.parse(fs.readFileSync(serverPath, "utf8"))
server.version = nextVersion
if (Array.isArray(server.packages) && server.packages.length > 0) {
  server.packages[0].version = nextVersion
}
fs.writeFileSync(serverPath, JSON.stringify(server, null, 2) + "\n")

const pyprojectPath = path.join(root, "pyproject.toml")
let pyproject = fs.readFileSync(pyprojectPath, "utf8")
pyproject = pyproject.replace(
  /^(\s*version\s*=\s*")[^"]+("\s*)$/m,
  `$1${nextVersion}$2`
)
fs.writeFileSync(pyprojectPath, pyproject)
